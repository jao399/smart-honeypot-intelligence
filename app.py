import os, json, math, io, base64, datetime, tempfile
from datetime import datetime, timedelta, UTC
from collections import defaultdict, deque, Counter, OrderedDict

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="Smart Smart Honeypot — RL + HITL",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_PATH_DEFAULT = "data/honeypots.json"
AGENT_SNAPSHOT_DIR = "snapshots"
# Directory where this script lives (fallback to cwd if __file__ not available)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
DEFAULT_DATA_PATH_ABS = os.path.join(SCRIPT_DIR, DATA_PATH_DEFAULT)
# Ensure snapshot dir is absolute relative to the script directory so
# saves/loads don't depend on the current working directory.
AGENT_SNAPSHOT_DIR_ABS = os.path.join(SCRIPT_DIR, AGENT_SNAPSHOT_DIR)
os.makedirs(AGENT_SNAPSHOT_DIR_ABS, exist_ok=True)

TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f"

def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    safe_df = df.copy()
    for col in safe_df.columns:
        safe_df[col] = safe_df[col].apply(
            lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
        )
    return safe_df

# -----------------------------
# Utilities: load + parse JSON
# -----------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        start = f.read(1)
        f.seek(0)
        if start == "[":
            return json.load(f)
        else:
            return [json.loads(line) for line in f]

def safe_int(x, default=None):
    try: return int(x)
    except: return default

def parse_time(ts):
    if ts is None: return None
    for fmt in (TIME_FMT, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            pass
    # fallback: pandas
    try:
        return pd.to_datetime(ts)
    except:
        return None

# -----------------------------
# Data preparation & sessionize
# -----------------------------
@st.cache_data
def load_and_prepare(path, session_gap_minutes=15):
    rows = load_json(path)
    df = pd.DataFrame(rows)
    # Ensure required columns exist
    for col in ["timestamp","src_ip","dest_port","protocol","action","src_port","dest_ip"]:
        if col not in df.columns:
            df[col] = None
    df["ts"] = df["timestamp"].apply(parse_time)
    # fill missing or bad times with increasing times
    if df["ts"].isnull().any():
        base = datetime(2023,1,1)
        null_mask = df["ts"].isnull()
        idxs = np.where(null_mask)[0]
        for i, idx in enumerate(idxs):
            df.at[idx, "ts"] = base + timedelta(seconds=i)
    df["dest_port"] = df["dest_port"].apply(lambda v: safe_int(v, v))
    df["src_port"] = df["src_port"].apply(lambda v: safe_int(v, v))
    df["service"] = df.apply(lambda r: infer_service(r.get("protocol"), r.get("dest_port")), axis=1)
    df["src_ip"] = df["src_ip"].astype(str)
    df = df.sort_values("ts").reset_index(drop=True)
    # sessionize by src_ip
    gap = timedelta(minutes=session_gap_minutes)
    sess_ids, last_ts = [], {}
    counts = defaultdict(int)
    for _, r in df.iterrows():
        ip = r["src_ip"]
        ts = r["ts"]
        if ip not in last_ts or ts - last_ts[ip] > gap:
            counts[ip] += 1
        sess_id = f"{ip}#{counts[ip]}"
        sess_ids.append(sess_id)
        last_ts[ip] = ts
    df["session_id"] = sess_ids
    return df

def infer_service(protocol, dest_port):
    p = str(protocol).lower() if protocol else ""
    port = safe_int(dest_port, -1)
    if p == "ssh" or port == 22: return "ssh"
    if p in ("http","https") or port in (80,8080,443): return "http"
    if p == "ftp" or port == 21: return "ftp"
    return "other"

# -----------------------------
# State buckets & helpers
# -----------------------------
def bucket_intensity(n):
    if n <= 2: return "low"
    if n <= 6: return "med"
    return "high"

def bucket_recency(minutes):
    if minutes is None: return "new"
    if minutes < 60: return "warm"
    return "frequent"

def state_from_event(event, ip_stats):
    service = event["service"]
    ip = event["src_ip"]
    now = event["ts"]
    cnt = ip_stats[ip].get("recent_count", 0)
    last_seen = ip_stats[ip].get("last_seen", None)
    rec_min = (now - last_seen).total_seconds()/60.0 if last_seen else None
    return (service, bucket_intensity(cnt), bucket_recency(rec_min))

# -----------------------------
# Environment
# -----------------------------
ACTIONS = ["default","banner_variation","latency_add","decoy_port_toggle","error_style_flip"]

class HoneypotEnv:
    def __init__(self, df, w1=1.0, w2=0.5, w3=0.2):
        self.df = df
        self._episodes = list(df["session_id"].unique())
        self._epi_idx = -1
        self.w1, self.w2, self.w3 = w1, w2, w3
        self.human_feedback = 0.0
        self.ip_stats = defaultdict(lambda: {"last_seen": None, "recent": deque(maxlen=50)})
        self._build_session_map()
        # metrics for visualization
        self.history = []

    def _build_session_map(self):
        self.by_session = {sid: self.df[self.df["session_id"]==sid].sort_values("ts").reset_index(drop=True)
                           for sid in self._episodes}

    def reset(self):
        self._epi_idx = (self._epi_idx + 1) % len(self._episodes)
        self.cur_sid = self._episodes[self._epi_idx]
        self.cur_df = self.by_session[self.cur_sid]
        self.ptr = 0
        # reset local ephemeral stats for this run
        return self._obs()

    def _obs(self):
        if self.ptr >= len(self.cur_df):
            return None
        ev = self.cur_df.iloc[self.ptr].to_dict()
        ip = ev["src_ip"]
        self.ip_stats[ip]["recent"].append(ev["ts"])
        self.ip_stats[ip]["last_seen"] = ev["ts"]
        self.ip_stats[ip]["recent_count"] = len(self.ip_stats[ip]["recent"])
        return state_from_event(ev, self.ip_stats)

    def step(self, action_idx):
        if self.ptr >= len(self.cur_df):
            return None, 0.0, True, {}
        ev = self.cur_df.iloc[self.ptr].to_dict()
        self.ptr += 1
        action = ACTIONS[action_idx]
        r = self._reward(ev, action) + self.human_feedback
        # logging for analysis
        self.history.append({
            "session": self.cur_sid,
            "event_idx": self.ptr-1,
            "timestamp": ev["ts"],
            "src_ip": ev["src_ip"],
            "service": ev["service"],
            "action": action,
            "reward": r,
            "human_feedback": self.human_feedback
        })
        self.human_feedback = 0.0
        done = self.ptr >= len(self.cur_df)
        obs = self._obs() if not done else None
        info = {"session_id": self.cur_sid, "action": action, "event_idx": self.ptr-1}
        return obs, r, done, info

    def _reward(self, ev, action):
        ses_len = len(self.cur_df)
        r1 = math.log1p(ses_len)
        ip = ev["src_ip"]
        recent_times = self.ip_stats[ip]["recent"]
        if len(recent_times) >= 2:
            deltas = [(recent_times[-1]-recent_times[-2]).total_seconds()]
            r2 = 1.0 if np.mean(deltas) < 180 else 0.0
        else:
            r2 = 0.0
        svc_div = len(set(self.cur_df["service"].tolist()))
        r3 = 1.0 if svc_div > 1 else 0.0
        mult = {
            "default": 1.0,
            "banner_variation": 1.05,
            "latency_add": 1.02,
            "decoy_port_toggle": 1.03,
            "error_style_flip": 1.01
        }[action]
        return mult * (self.w1*r1 + self.w2*r2 + self.w3*r3)

# -----------------------------
# Agent: Tabular Q-Learning
# -----------------------------
class QAgent:
    def __init__(self, actions=ACTIONS, alpha=0.2, gamma=0.95, eps=0.2):
        self.actions = list(actions)
        self.alpha, self.gamma, self.eps = alpha, gamma, eps
        self.Q = defaultdict(lambda: np.zeros(len(self.actions), dtype=float))
        # training trace for visuals
        self.episode_rewards = []
        self.best_action_history = []

    def select(self, state):
        if (state is None) or (np.random.rand() < self.eps):
            return np.random.randint(len(self.actions))
        return int(np.argmax(self.Q[state]))

    def update(self, s, a, r, s2, done):
        qsa = self.Q[s][a]
        if done:
            target = r
        else:
            # ensure s2 exists in Q table
            _ = self.Q[s2]
            target = r + self.gamma * np.max(self.Q[s2])
        self.Q[s][a] = qsa + self.alpha * (target - qsa)

    def snapshot(self, path):
        # Save Q table to numpy (simple)
        arrs = {str(k): v.tolist() for k, v in self.Q.items()}
        np.save(path, arrs, allow_pickle=True)

    def load_snapshot(self, path):
        arrs = np.load(path, allow_pickle=True).item()
        self.Q = defaultdict(lambda: np.zeros(len(self.actions), dtype=float))
        for k, v in arrs.items():
            # convert key string back to tuple
            key = eval(k)
            self.Q[key] = np.array(v)

# -----------------------------
# Helper: export CSV / PNG
# -----------------------------
def get_table_download_link(df, filename="export.csv"):
    csv = df.to_csv(index=False).encode()
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV</a>'
    return href

def fig_to_png_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

# -----------------------------
# Streamlit App Layout & Logic
# -----------------------------
def main():
    st.header("Smart Honeypot Intelligence - (Adaptive Defense with Reinforcement Learning and Human Feedback)")
    st.markdown("""
    **Overview:** This platform leverages reinforcement learning and human expertise to adaptively manage honeypot interactions. By analyzing sessionized network activity and applying machine-learning-driven strategies, it enables security teams to understand attacker behavior, evaluate response effectiveness, and optimize defensive tactics.
    """)

    # -------------------------
    # Sidebar: Global config
    # -------------------------
    with st.sidebar:
        st.subheader("Dataset & Environment")
        # Allow specifying a path or uploading a dataset. Upload takes precedence.
        data_path_input = st.text_input("Dataset Path (JSON)", DATA_PATH_DEFAULT)
        uploaded_file = st.file_uploader("Or upload dataset (JSON)", type=["json"])
        if uploaded_file is not None:
            # Save uploaded file to a temporary file and use that path
            tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
            tmpf.write(uploaded_file.getvalue())
            tmpf.flush()
            tmpf.close()
            data_path = tmpf.name
            st.success(f"Uploaded dataset saved to temporary file: {data_path}")
        else:
            data_path = data_path_input
        session_gap = st.number_input("Session gap (minutes)", min_value=1, max_value=720, value=15)
        st.caption("Define the idle time (in minutes) after which a new session is created for the same source IP.")

        st.subheader("RL Hyperparameters")
        alpha = st.slider("Learning Rate (Alpha): Controls how quickly the agent updates its knowledge during training.", 0.01, 1.0, 0.2, 0.01)
        gamma = st.slider("Discount Factor (Gamma): Balances the importance of short-term vs. long-term rewards.", 0.0, 0.999, 0.95, 0.01)
        eps = st.slider("Exploration Rate (Epsilon): Determines how often the agent explores new actions rather than exploiting known ones.", 0.0, 1.0, 0.2, 0.01)
        episodes = st.number_input("Episodes per Run: Number of training episodes to execute per training cycle.", 1, 2000, 20)
        st.subheader("Reward Weights")
        w1 = st.number_input("Session Length (w1): Prioritize keeping attackers engaged longer.", 0.0, 10.0, 1.0, 0.1)
        w2 = st.number_input("Follow-up Activity (w2): Reward repeated interactions from the same source IP.", 0.0, 10.0, 0.5, 0.1)
        w3 = st.number_input("Service Diversity (w3): Encourage interactions across multiple services.", 0.0, 10.0, 0.2, 0.1)

        st.markdown("---")
        st.write("Agent snapshots (save/load)")
        snapshot_name = st.text_input("Snapshot Name: Provide a name for saving or loading agent state snapshots.", value="agent_snapshot")
        if st.button("Save snapshot"):
            # Always save to the absolute snapshots folder next to the script
            path = os.path.join(AGENT_SNAPSHOT_DIR_ABS, f"{snapshot_name}.npy")
            if "agent" in st.session_state:
                st.session_state.agent.snapshot(path)
                st.success(f"Saved agent snapshot to {path}")
            else:
                st.warning("No agent in session to save.")

        if st.button("Load snapshot"):
            # Try several sensible locations for the snapshot so the app finds
            # files even if the working directory changed since the file was created.
            requested = f"{snapshot_name}.npy"
            candidates = [
                os.path.join(AGENT_SNAPSHOT_DIR_ABS, requested),
                os.path.join(SCRIPT_DIR, requested),
                os.path.join(os.getcwd(), AGENT_SNAPSHOT_DIR, requested),
                os.path.join(os.getcwd(), requested),
                requested,
            ]
            resolved = None
            tried = []
            for p in candidates:
                if p in tried:
                    continue
                tried.append(p)
                try:
                    if os.path.exists(p):
                        resolved = p
                        break
                except Exception:
                    pass

            if resolved is None:
                st.error(f"Snapshot not found: {snapshot_name}")
                st.info("Paths attempted:")
                for p in tried:
                    st.text(p)
            else:
                if "agent" not in st.session_state:
                    st.session_state.agent = QAgent(alpha=alpha, gamma=gamma, eps=eps)
                st.session_state.agent.load_snapshot(resolved)
                st.success(f"Loaded snapshot from {resolved}")

        st.markdown("---")
        st.write("Export")
        st.caption("Use the Export buttons in the tabs to download charts, logs, or Q-table snapshots in CSV or PNG format for offline analysis or reporting.")

    # -------------------------
    # Load data & create env/agent
    # -------------------------
    # Try to robustly resolve the dataset path in a few sensible locations so the
    # app still works if the working directory changed since yesterday.
    tried_paths = []
    resolved = None
    candidates = [data_path, os.path.join(SCRIPT_DIR, data_path), os.path.join(os.getcwd(), data_path), DEFAULT_DATA_PATH_ABS]
    # keep unique while preserving order
    seen = set()
    uniq_candidates = []
    for p in candidates:
        if p and p not in seen:
            uniq_candidates.append(p)
            seen.add(p)

    for p in uniq_candidates:
        tried_paths.append(p)
        try:
            if os.path.exists(p):
                resolved = p
                break
        except Exception:
            pass

    if resolved is None:
        st.warning("Dataset not found — please provide a valid path in the sidebar.")
        st.info("Paths attempted:")
        for p in tried_paths:
            st.text(p)
        st.stop()
    else:
        data_path = resolved
        st.info(f"Using dataset: {data_path}")

    df = load_and_prepare(data_path, session_gap_minutes=session_gap)
    st.success(f"Loaded dataset with {len(df)} events and {df['session_id'].nunique()} sessions.")

    # init session_state
    if "env" not in st.session_state or st.button("Recreate environment (reset state)"):
        st.session_state.env = HoneypotEnv(df, w1=w1, w2=w2, w3=w3)
        st.session_state.agent = QAgent(alpha=alpha, gamma=gamma, eps=eps)
        st.session_state.train_counter = 0
        st.session_state.audit_log = []
        st.session_state.metrics = {"episode_rewards": [], "action_counts": Counter(), "state_visits": Counter()}

    env = st.session_state.env
    agent = st.session_state.agent

    # -------------------------
    # Top-level Controls (columns)
    # -------------------------
    c1, c2, c3 = st.columns([2,2,3])
    with c1:
        st.subheader("Training Controls")
        run_train = st.button("Run Training Episodes")
        reset_q = st.button("Reset Q-table")
        if reset_q:
            st.session_state.agent = QAgent(alpha=alpha, gamma=gamma, eps=eps)
            st.success("Q-table reset.")
    with c2:
        st.subheader("Human Feedback Controls")
        st.write("Global feedback (applies to next step by default)")
        hf_value = st.slider("Global feedback value", -5.0, 5.0, 0.0, 0.1)
        hf_apply_next = st.button("Apply global feedback to next step")
        st.text_input("Analyst note (optional)", key="analyst_note")
    with c3:
        st.subheader("Experiment Controls")
        st.write("Use snapshots to record policies at milestones.")
        st.write("Train episodes per click (sidebar setting)")

    # -------------------------
    # Run training if requested
    # -------------------------
    if run_train:
        ep_rewards = []
        for e in range(int(episodes)):
            s = env.reset()
            done = False
            ep_reward = 0.0
            steps = 0
            while not done:
                a = agent.select(s)
                # apply global feedback if user requested it
                if hf_apply_next:
                    env.human_feedback = float(hf_value)
                    # audit
                    st.session_state.audit_log.append({
                        "time": datetime.now(UTC),
                        "type": "global_feedback",
                        "value": float(hf_value),
                        "note": st.session_state.get("analyst_note", "")
                    })
                s2, r, done, info = env.step(a)
                # update metrics for visuals
                st.session_state.metrics["action_counts"][ACTIONS[a]] += 1
                if s is not None:
                    st.session_state.metrics["state_visits"][s] += 1
                agent.update(s, a, r, s2, done)
                ep_reward += r
                s = s2
                steps += 1
            agent.episode_rewards.append(ep_reward)
            st.session_state.env.history = [dict(x) for x in env.history] 
            st.session_state.train_counter += 1
            st.session_state.metrics["episode_rewards"].append(ep_reward)
            st.session_state.audit_log.append({
                "time": datetime.now(UTC),
                "type": "episode_end",
                "episode": st.session_state.train_counter,
                "reward": ep_reward,
                "steps": steps
            })
            ep_rewards.append(ep_reward)
        st.success(f"Completed {episodes} episodes. Most recent episode reward: {ep_rewards[-1]:.3f}")

    # -------------------------
    # Tabs: Dashboard, Train, HITL, Visuals, Exports, Audit
    # -------------------------
    st.markdown(
    """
    <style>
    /* Make tabs larger and bolder */
    div[data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: 600 !important;
        padding: 12px 20px !important;
    }
    /* Active tab styling */
    div[data-baseweb="tab"][aria-selected="true"] {
        background-color: #f0f2f6 !important;
        border-radius: 10px !important;
        color: #1a1a1a !important;
        box-shadow: 0px 2px 6px rgba(0, 0, 0, 0.1);
    }
    /* Hover effect */
    div[data-baseweb="tab"]:hover {
        background-color: #f9fafb !important;
        color: #000000 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
    )

# -----------------------------
# TAB DEFINITIONS
# -----------------------------
    tabs = st.tabs([
        "Overview",
        "Training",
        "HITL Feedback",
        "Visualizations",
        "Agent / Policy",
        "Exports",
        "Audit Log"
        ])

    ###############
    # Overview tab
    ###############
    with tabs[0]:
        st.subheader("Dataset Overview")
        st.write(f"View key statistics and Summary data from your honeypot logs, including event counts, sessions, top IPs, and service usage trends.")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total events", len(df))
            st.metric("Unique sessions", df["session_id"].nunique())
        with col2:
            st.metric("Unique source IPs", df["src_ip"].nunique())
            st.metric("Time span", f"{df['ts'].min()} → {df['ts'].max()}")
        with col3:
            st.metric("Service types", df["service"].nunique())
            st.metric("Actions types", df["action"].nunique())

        st.markdown("**Sample rows**")
        st.dataframe(sanitize_df(df.head(200)))
        
        st.markdown("**Top source IPs**")
        top_src = df["src_ip"].value_counts().rename_axis("src_ip").reset_index(name="events").head(20)
        st.dataframe(sanitize_df(top_src))

    ###############
    # Training tab
    ###############
    with tabs[1]:
        st.subheader("Training controls & recent metrics")
        st.write(f"Monitor reinforcement learning progress, including reward trends and recent session activity during training runs.")
        st.write(f"Total training episodes run: {st.session_state.get('train_counter', 0)}")
        if st.session_state.agent.episode_rewards:
            srs = pd.Series(st.session_state.agent.episode_rewards)
            st.line_chart(srs.rolling(5,min_periods=1).mean().rename("episode_reward_moving_avg"))
            st.write("Latest episode rewards (last 50)")
            st.dataframe(pd.DataFrame({"episode_reward": st.session_state.agent.episode_rewards[-50:]}))
        st.markdown("**Recent env history (events processed)**")
        if hasattr(env, "history") and env.history:
            hist_df = pd.DataFrame(env.history[-500:])
            st.dataframe(sanitize_df(hist_df.tail(200)))
        else:
            st.info("No training history yet. Run some episodes to populate history.")

    ###############
    # HITL Feedback tab
    ###############
    with tabs[2]:
        st.subheader("Human-in-the-loop Feedback Panel")
        st.write("Provide targeted human feedback to influence agent learning. Adjust rewards for specific sessions, apply overrides, or annotate interactions for future reference.")
        audit_log = st.session_state.get("audit_log", [])
        notes = [a for a in audit_log if a.get("type") in ("global_feedback", "per_session_feedback")]
        cols = st.columns([2,2,2])
        with cols[0]:
            selected_session = st.selectbox("Select a session to inspect (session_id)", options=list(df["session_id"].unique())[:500])
            if st.button("Inspect session events"):
                sdd = df[df["session_id"]==selected_session].sort_values("ts")
                if notes:
                    st.dataframe(sanitize_df(pd.DataFrame(notes).tail(50)))
        with cols[1]:
            per_fb = st.slider("Per-session feedback (-5 to +5)", -5.0, 5.0, 0.0, 0.1)
            if st.button("Apply feedback to selected session (applies to next step for that session)"):
                if not hasattr(env, "feedback_map"):
                    env.feedback_map = {}
                env.feedback_map[selected_session] = float(per_fb)
                st.session_state.audit_log.append({
                    "time": datetime.now(UTC),
                    "type": "per_session_feedback",
                    "session": selected_session,
                    "value": per_fb,
                    "note": st.session_state.get("analyst_note","")
                })
                st.success(f"Stored feedback {per_fb} for {selected_session}. It will apply when env plays that session.")
        with cols[2]:
            st.write("Manual action override (for experiments)")
            ov_action = st.selectbox("Force action for next step (optional)", options=["none"]+ACTIONS)
            if st.button("Set override for next step"):
                env.next_action_override = None if ov_action=="none" else ov_action
                st.session_state.audit_log.append({
                    "time": datetime.now(UTC),
                    "type": "manual_override",
                    "override": ov_action
                })
                st.success(f"Next step overridden to {ov_action}")

        st.markdown("**Analyst notes history (last 50)**")
        if notes:
            st.dataframe(pd.DataFrame(notes).tail(50))
        else:
            st.info("No analyst feedback recorded yet.")

    ###############
    # Visualizations tab
    ###############
    with tabs[3]:
        st.subheader("Interactive Visualizations")
        st.markdown(
            "Analyze traffic patterns, agent behavior, and training performance with "
            "dynamic, publication-ready charts and filters."
        )

    # -----------------------------
    # GLOBAL FILTERS
    # -----------------------------
    st.markdown("### Filter Data")
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_services = st.multiselect(
            "Select services",
            options=sorted(df["service"].unique()),
            default=sorted(df["service"].unique())
        )
    with col2:
        date_range = st.date_input(
            "Date range",
            value=[df["ts"].min().date(), df["ts"].max().date()],
        )
    with col3:
        top_n_ips = st.slider("Top N IPs", 5, 50, 30)

    # Apply filters to data
    df_filtered = df[
        (df["service"].isin(selected_services)) &
        (df["ts"].dt.date >= date_range[0]) &
        (df["ts"].dt.date <= date_range[1])
    ]

    st.info(f"Showing {len(df_filtered):,} events after filtering.")

    # Optional CSV export
    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data",
        data=csv,
        file_name="filtered_honeypot_data.csv",
        mime="text/csv",
    )

    # -----------------------------
    # CHART TABS
    # -----------------------------
    chart_tabs = st.tabs([
        "Traffic Patterns",
        "RL Training Metrics",
        "Agent Insights",
        "Human Feedback"
    ])

    # =============================
    # TAB 1: TRAFFIC PATTERNS
    # =============================
    with chart_tabs[0]:
        st.subheader("Traffic Patterns")

        # Sessions per service
        svc_counts = df_filtered.groupby("service")["session_id"].nunique().reset_index(name="sessions")
        fig1 = px.bar(
            svc_counts, x="service", y="sessions",
            title="Sessions per Service",
            hover_data=["sessions"], text="sessions"
        )
        fig1.update_traces(texttemplate='%{text}', textposition='outside')
        st.plotly_chart(fig1, use_container_width=True)

        # Events over time
        by_time = df_filtered.set_index("ts").resample("1h").size().rename("events").reset_index()
        fig2 = px.line(
            by_time, x="ts", y="events",
            title="Events Over Time (Hourly)",
            markers=True
        )
        fig2.update_xaxes(rangeslider_visible=True)
        st.plotly_chart(fig2, use_container_width=True)

        # Top source IPs
        top_src = df_filtered["src_ip"].value_counts().head(top_n_ips).reset_index()
        top_src.columns = ["src_ip", "events"]
        fig4 = px.bar(
            top_src, x="src_ip", y="events",
            title=f"Top {top_n_ips} Source IPs by Events",
            hover_data=["events"]
        )
        st.plotly_chart(fig4, use_container_width=True)

        # Session length distribution
        sess_len = df_filtered.groupby("session_id").size().rename("len").reset_index()
        fig3 = px.histogram(
            sess_len, x="len", nbins=50,
            title="Session Length Distribution",
            marginal="box"
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Heatmap: service activity by hour/day
        df_filtered["hour"] = df_filtered["ts"].dt.hour
        df_filtered["dow"] = df_filtered["ts"].dt.day_name()
        pivot = df_filtered.groupby(["service", "dow", "hour"]).size().reset_index(name="count")
        for svc in pivot["service"].unique():
            svc_df = pivot[pivot["service"] == svc]
            if not svc_df.empty:
                fig13 = px.density_heatmap(
                    svc_df, x="hour", y="dow", z="count",
                    title=f"Activity Heatmap — {svc}"
                )
                st.plotly_chart(fig13, use_container_width=True)

    # =============================
    # TAB 2: RL TRAINING METRICS
    # =============================
    with chart_tabs[1]:
        st.subheader("RL Training Metrics")

        if st.session_state.metrics["episode_rewards"]:
            er = pd.Series(st.session_state.metrics["episode_rewards"], name="episode_reward")
            df_er = er.reset_index().rename(columns={"index": "episode"})
            df_er["ma5"] = df_er["episode_reward"].rolling(5, min_periods=1).mean()
            fig6 = px.line(
                df_er, x="episode", y=["episode_reward", "ma5"],
                title="Episode Rewards and Moving Average"
            )
            st.plotly_chart(fig6, use_container_width=True)

            cumul = np.cumsum(st.session_state.metrics["episode_rewards"])
            fig11 = px.line(
                x=np.arange(len(cumul)), y=cumul,
                title="Cumulative Reward Over Training"
            )
            st.plotly_chart(fig11, use_container_width=True)

        ac = pd.DataFrame.from_records(
            list(st.session_state.metrics["action_counts"].items()),
            columns=["action", "count"]
        )
        if not ac.empty:
            fig7 = px.bar(ac, x="action", y="count", title="Counts of Actions During Training")
            st.plotly_chart(fig7, use_container_width=True)

    # =============================
    # TAB 3: AGENT INSIGHTS
    # =============================
    with chart_tabs[2]:
        st.subheader("Agent Insights")

        sv = pd.DataFrame.from_records(
            [(k, v) for k, v in st.session_state.metrics["state_visits"].items()],
            columns=["state", "visits"]
        )
        if not sv.empty:
            sv["state_str"] = sv["state"].apply(str)
            fig8 = px.bar(
                sv.sort_values("visits", ascending=False).head(40),
                x="state_str", y="visits",
                title="Top Visited States"
            )
            st.plotly_chart(fig8, use_container_width=True)

        with st.expander("Q-Value Heatmap (Sample of 80 States)"):
            q_items = list(agent.Q.items())[:80]
            if q_items:
                qs = np.stack([v for _, v in q_items])
                fig9, ax9 = plt.subplots(figsize=(9, 6))
                sns.heatmap(qs, ax=ax9, cmap="viridis")
                ax9.set_ylabel("State Index")
                ax9.set_xlabel("Action Index")
                st.pyplot(fig9)

        best_counts = Counter()
        for s, q in agent.Q.items():
            best = int(np.argmax(q))
            best_counts[ACTIONS[best]] += 1
        bc_df = pd.DataFrame(list(best_counts.items()), columns=["action", "best_count"])
        if not bc_df.empty:
            fig20 = px.bar(
                bc_df, x="action", y="best_count",
                title="Number of States Where Action is Optimal"
            )
            st.plotly_chart(fig20, use_container_width=True)

    # =============================
    # TAB 4: HUMAN FEEDBACK
    # =============================
    with chart_tabs[3]:
        st.subheader("Human Feedback")
        fb_logs = [a for a in st.session_state.audit_log if a.get("type") in ("global_feedback", "per_session_feedback")]
        if fb_logs:
            df_fb = pd.DataFrame(fb_logs)
            df_fb["time"] = pd.to_datetime(df_fb["time"])
            fig17 = px.scatter(
                df_fb, x="time", y="value", color="type",
                title="Human Feedback Timeline",
                hover_data=["value", "notes"] if "notes" in df_fb else ["value"]
            )
            st.plotly_chart(fig17, use_container_width=True)
        else:
            st.info("No human feedback logs recorded yet.")


    ###############
    # Agent / Policy tab
    ###############
    with tabs[4]:
        st.subheader("Agent / Q-table")
        st.write("Inspect the agent’s current Q-table and review which actions are preferred for specific states to understand policy evolution.")
        qitems = []
        for s,q in list(agent.Q.items())[:200]:
            qitems.append({"state": str(s), "best_action": ACTIONS[int(np.argmax(q))], "Q_values": list(np.round(q,3))})
        if qitems:
            st.dataframe(sanitize_df(pd.DataFrame(qitems)))
        else:
            st.info("Q-table is empty. Train the agent to populate Q values.")

        st.markdown("**Policy explanation:**")
        st.write("For any state, the agent picks the action with highest Q-value. Use snapshots to compare policy changes across training runs.")

    ###############
    # Exports tab
    ###############
    with tabs[5]:
        st.subheader("Export logs and snapshots")
        st.write("Export training histories, audit logs, and Q-table snapshots for reporting or offline analysis.")
        if hasattr(env, "history") and env.history:
            hist_df = pd.DataFrame(env.history)
            st.markdown(get_table_download_link(hist_df, filename="env_history.csv"), unsafe_allow_html=True)
        if st.session_state.audit_log:
            st.markdown(get_table_download_link(pd.DataFrame(st.session_state.audit_log), filename="audit_log.csv"), unsafe_allow_html=True)
        if st.button("Download Q-table (npz)"):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".npy")
            agent.snapshot(tmp.name)
            with open(tmp.name, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="qtable_snapshot.npy">Download Q-table</a>'
            st.markdown(href, unsafe_allow_html=True)

    ###############
    # Audit Log tab
    ###############
    with tabs[6]:
        st.subheader("Audit Log")
        st.write("Review a timestamped log of analyst interventions, feedback, and system events to maintain a transparent record of activity.")
        if st.session_state.audit_log:
            df_audit = pd.DataFrame(st.session_state.audit_log)
            st.dataframe(sanitize_df(df_audit.sort_values("time", ascending=False)))
        else:
            st.info("No audit events recorded yet. Analyst actions and episode completions will appear here.")

    # -------------------------
    # Footer: Safety reminder
    # -------------------------
    st.markdown("---")
    st.info("© 2025 Smart Honeypot Intelligence Powered by adaptive reinforcement learning and human-in-the-loop strategies to enhance security visibility and threat response - *Made By Amjad For Educational Purpose Only*.")

if __name__ == "__main__":
    main()
