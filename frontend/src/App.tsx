// @ts-nocheck
import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  Bell,
  Camera,
  CameraOff,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  Filter,
  LayoutDashboard,
  Menu,
  Mic,
  MicOff,
  Mic2,
  Moon,
  Plus,
  Search,
  Sparkles,
  Square,
  Target,
  Users,
  Zap,
} from "lucide-react";
import { api, ApiAction, ApiMeeting } from "./api";
import en from "./locales/en.json";
import hi from "./locales/hi.json";
import te from "./locales/te.json";
import ta from "./locales/ta.json";
import kn from "./locales/kn.json";
import ml from "./locales/ml.json";
import mr from "./locales/mr.json";
import bn from "./locales/bn.json";

type Page = "dashboard" | "meeting" | "actions" | "new" | "search" | "room";
const demoSegments = [
  [
    "00:00",
    "Maya Chen",
    "Welcome everyone. Today we are aligning the Apollo release plan and removing the last blockers for beta.",
    "Opening",
  ],
  [
    "04:12",
    "Marcus Taylor",
    "The API gateway is stable in staging. The remaining work is observability and the payment retry path.",
    "Engineering update",
  ],
  [
    "09:38",
    "Priya Nair",
    "I can own the authentication issue. I will have the callback handling fixed by tomorrow afternoon.",
    "Commitment",
  ],
  [
    "12:41",
    "Priya Nair",
    "We should use PostgreSQL for reporting because the audit trail needs relational queries and predictable backups.",
    "Technical decision",
  ],
  [
    "18:42",
    "Marcus Taylor",
    "The load test is the gate for beta. I will publish the report before Thursday so we can review it together.",
    "Release readiness",
  ],
  [
    "23:17",
    "Elena Rossi",
    "We cannot deploy Friday without a security review. I will schedule it, but the compliance approval is still missing.",
    "Risk",
  ],
  [
    "28:15",
    "Maya Chen",
    "Decision: beta deployment is Friday, provided the load test and security review are green. Let us reconvene Wednesday.",
    "Decision",
  ],
  [
    "31:04",
    "Maya Chen",
    "Open question: do we support regional data residency in the first beta, or is that a post-beta commitment?",
    "Open question",
  ],
] as const;

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [dark, setDark] = useState(false);
  const [menu, setMenu] = useState(false);
  const [meetings, setMeetings] = useState<ApiMeeting[]>([]);
  const [actions, setActions] = useState<ApiAction[]>([]);
  const [selected, setSelected] = useState<ApiMeeting | null>(null);
  const [error, setError] = useState("");
  const [language, setLanguage] = useState("en");
  const [notifications, setNotifications] = useState<
    Array<{ id: string; title: string; body: string; read: boolean }>
  >([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const catalogs = { en, hi, te, ta, kn, ml, mr, bn } as const;
  const copy = catalogs[language as keyof typeof catalogs] ?? en;
  useEffect(() => {
    api
      .bootstrap()
      .then(({ meetings, actions }) => {
        setMeetings(meetings);
        setActions(actions);
        const demo = meetings.find((m) => m.is_demo);
        if (demo) setSelected(demo);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "API unavailable"),
      );
    Promise.all([api.profile(), api.notifications()])
      .then(([profile, notificationData]) => {
        setLanguage(profile.language);
        setNotifications(notificationData.items);
      })
      .catch(() => undefined);
  }, []);
  const changeLanguage = async (next: string) => {
    try {
      const profile = await api.profile();
      await api.updateProfile({
        language: next,
        timezone: profile.timezone,
        notifications_enabled: profile.notifications_enabled,
      });
      setLanguage(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save language");
    }
  };
  const markNotification = async (id: string) => {
    await api.markNotification(id);
    setNotifications(
      notifications.map((item) =>
        item.id === id ? { ...item, read: true } : item,
      ),
    );
  };
  const openMeeting = (meeting: ApiMeeting | null = selected) => {
    if (meeting) {
      setSelected(meeting);
      setPage("meeting");
    }
  };
  return (
    <div className={dark ? "app dark" : "app"}>
      <aside className={menu ? "sidebar open" : "sidebar"}>
        <div className="brand">
          <div className="brand-mark">
            <Sparkles size={16} />
          </div>
          <span>
            meetmind<span className="muted">.ai</span>
          </span>
        </div>
        <div className="workspace">
          <div className="avatar">JD</div>
          <div>
            <strong>Jordan Davis</strong>
            <small>Product workspace</small>
          </div>
          <ChevronRight size={15} />
        </div>
        <nav>
          <Nav
            icon={<LayoutDashboard />}
            label={copy.overview}
            active={page === "dashboard"}
            onClick={() => setPage("dashboard")}
          />
          <Nav
            icon={<FileText />}
            label={copy.meetings}
            active={page === "meeting"}
            onClick={() => openMeeting()}
          />
          <Nav
            icon={<Target />}
            label={copy.actions}
            active={page === "actions"}
            onClick={() => setPage("actions")}
            badge={String(
              actions.filter((a) => a.status !== "Completed").length,
            )}
          />
          <Nav
            icon={<Search />}
            label={copy.search}
            active={page === "search"}
            onClick={() => setPage("search")}
          />
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy">
            <Sparkles size={16} />
            <span>
              <strong>Demo mode</strong>
              <small>Provider-safe workspace</small>
            </span>
          </div>
          <Nav icon={<Zap />} label="AI provider status" />
        </div>
      </aside>
      <main>
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setMenu(!menu)}>
            <Menu size={20} />
          </button>
          <div className="crumb">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>
              {page === "meeting"
                ? "Project Apollo · Sprint Planning"
                : page === "actions"
                  ? "Action center"
                  : page === "new"
                    ? "New meeting"
                    : page === "search"
                      ? "Meeting memory"
                      : "Overview"}
            </strong>
          </div>
          <div className="top-actions">
            <button
              className="search-shortcut"
              onClick={() => setPage("search")}
            >
              <Search size={16} />
              <span>Search meetings...</span>
              <kbd>⌘ K</kbd>
            </button>
            <select
              aria-label="Language"
              value={language}
              onChange={(event) => changeLanguage(event.target.value)}
              style={{
                border: "1px solid var(--line)",
                borderRadius: 7,
                padding: "7px 5px",
                background: "var(--panel)",
                color: "var(--ink)",
                fontSize: 10,
              }}
            >
              <option value="en">EN</option>
              <option value="hi">हिं</option>
              <option value="te">తె</option>
              <option value="ta">த</option>
              <option value="kn">ಕ</option>
              <option value="ml">മ</option>
              <option value="mr">म</option>
              <option value="bn">বা</option>
            </select>
            <button
              className="icon-btn"
              onClick={() => setShowNotifications(!showNotifications)}
            >
              <Bell size={18} />
            </button>
            <button className="icon-btn" onClick={() => setDark(!dark)}>
              {dark ? <Zap size={18} /> : <Moon size={18} />}
            </button>
            <div className="avatar avatar-sm">JD</div>
          </div>
          {showNotifications && (
            <div className="notification-popover">
              {notifications.length === 0 ? (
                <span className="muted">No notifications</span>
              ) : (
                notifications.map((item) => (
                  <button
                    key={item.id}
                    className={item.read ? "notification read" : "notification"}
                    onClick={() => markNotification(item.id)}
                  >
                    <strong>{item.title}</strong>
                    <small>{item.body}</small>
                  </button>
                ))
              )}
            </div>
          )}
        </header>
        {error && (
          <div className="api-notice">
            API unavailable: {error}. Demo data is not shown as persisted.
          </div>
        )}
        {page === "dashboard" && (
          <Dashboard
            meetings={meetings}
            actions={actions}
            onNew={() => setPage("new")}
            onRoom={() => setPage("room")}
            onOpen={openMeeting}
          />
        )}{" "}
        {page === "meeting" && (
          <Meeting
            meeting={selected}
            meetings={meetings}
            onBack={() => setPage("dashboard")}
          />
        )}{" "}
        {page === "actions" && (
          <Actions actions={actions} setActions={setActions} />
        )}{" "}
        {page === "new" && (
          <NewMeeting
            onBack={() => setPage("dashboard")}
            onDone={(meeting) => {
              setMeetings([meeting, ...meetings]);
              setSelected(meeting);
              setPage("meeting");
            }}
          />
        )}
        {page === "search" && <SearchPage onOpen={openMeeting} />}
        {page === "room" && (
          <Room
            onBack={() => setPage("dashboard")}
            onDone={(meeting) => {
              setMeetings([meeting, ...meetings]);
              setSelected(meeting);
              setPage("meeting");
            }}
          />
        )}
      </main>
    </div>
  );
}
function Nav({
  icon,
  label,
  active,
  onClick,
  badge,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
  badge?: string;
}) {
  return (
    <button
      className={active ? "nav-item active" : "nav-item"}
      onClick={onClick}
    >
      {icon}
      <span>{label}</span>
      {badge && <em>{badge}</em>}
    </button>
  );
}
function Dashboard({
  meetings,
  actions,
  onNew,
  onOpen,
}: {
  meetings: ApiMeeting[];
  actions: ApiAction[];
  onNew: () => void;
  onRoom: () => void;
  onOpen: (m?: ApiMeeting | null) => void;
}) {
  const demo = meetings.find((m) => m.is_demo);
  return (
    <div className="page">
      <section className="welcome">
        <div>
          <p className="eyebrow">
            <span className="pulse" /> MONDAY, OCTOBER 05, 2026
          </p>
          <h1>
            Good morning, Jordan <span>✦</span>
          </h1>
          <p className="lead">Your meetings are becoming momentum.</p>
        </div>
        <button className="primary" onClick={onNew}>
          <Plus size={17} /> Analyze a meeting
        </button>
      </section>
      <div className="metrics">
        <Metric
          label="Meetings analyzed"
          value={String(meetings.length)}
          delta="Persisted"
          icon={<FileText />}
        />
        <Metric
          label="Open actions"
          value={String(actions.filter((a) => a.status !== "Completed").length)}
          delta="Live data"
          icon={<Target />}
        />
        <Metric
          label="Evidence segments"
          value={demo ? "8" : "0"}
          delta="Traceable"
          icon={<Activity />}
        />
        <Metric
          label="AI provider"
          value="Demo"
          delta="Configured"
          icon={<Sparkles />}
        />
      </div>
      <div className="grid-2">
        <section className="panel pulse-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">WORKSPACE SIGNAL</p>
              <h2>AI Pulse</h2>
            </div>
            <span className="live-tag">
              <i /> Live
            </span>
          </div>
          <div className="pulse-layout">
            <div className="score-ring">
              <strong>82</strong>
              <span>/100</span>
              <small>meeting health</small>
            </div>
            <div className="signal-list">
              <Signal
                text={`${actions.filter((a) => a.status !== "Completed").length} open actions`}
                tone="violet"
              />
              <Signal text="Transcript evidence available" tone="orange" />
              <Signal text="Provider-safe demo mode" tone="red" />
            </div>
          </div>
        </section>
        <section className="panel next-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">YOUR FOCUS</p>
              <h2>Next up</h2>
            </div>
          </div>
          {demo ? (
            <button className="focus-card" onClick={() => onOpen(demo)}>
              <div className="focus-icon">
                <FileText size={20} />
              </div>
              <div>
                <strong>{demo.title}</strong>
                <p>{demo.actions.length} persisted actions</p>
                <small>
                  <Clock3 size={13} /> Evidence-linked demo
                </small>
              </div>
              <ArrowUpRight size={16} />
            </button>
          ) : (
            <p className="muted">No meetings yet. Create one to begin.</p>
          )}
          <button className="outline wide" onClick={onRoom}>
            <Mic2 size={16} /> Start a live recording
          </button>
        </section>
      </div>
      <section className="panel meetings-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">RECENT INTELLIGENCE</p>
            <h2>Recent meetings</h2>
          </div>
        </div>
        {meetings.map((m) => (
          <button className="meeting-row" key={m.id} onClick={() => onOpen(m)}>
            <div className="meeting-icon violet">
              <FileText size={19} />
            </div>
            <div className="meeting-name">
              <strong>{m.title}</strong>
              <span>{m.status}</span>
            </div>
            <span className="status">
              <i /> {m.is_demo ? "DEMO DATA" : "Persisted"}
            </span>
            <ChevronRight size={16} />
          </button>
        ))}
      </section>
    </div>
  );
}
function Metric({
  label,
  value,
  delta,
  icon,
}: {
  label: string;
  value: string;
  delta: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="metric">
      <div className="metric-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{delta}</small>
      </div>
    </div>
  );
}
function Signal({ text, tone }: { text: string; tone: string }) {
  return (
    <div className="signal">
      <span className={`signal-dot ${tone}`} />
      <span>{text}</span>
      <ChevronRight size={15} />
    </div>
  );
}
function Meeting({
  meeting,
  meetings,
  onBack,
}: {
  meeting: ApiMeeting | null;
  meetings: ApiMeeting[];
  onBack: () => void;
}) {
  const [tab, setTab] = useState("Overview");
  const [comparison, setComparison] = useState<any>(null);
  const [compareId, setCompareId] = useState("");
  const [query, setQuery] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<{
    answer: string;
    confidence: number;
    evidence: Array<{ timestamp: string; speaker: string; text?: string }>;
  } | null>(null);
  const [segments, setSegments] = useState<
    | typeof demoSegments
    | Array<{ timestamp: string; speaker: string; text: string; topic: string }>
  >(demoSegments);
  useEffect(() => {
    if (meeting && !meeting.is_demo)
      api
        .transcript(meeting.id)
        .then((r) => setSegments(r.items))
        .catch(() => {});
  }, [meeting]);
  if (!meeting)
    return (
      <div className="page">
        <Empty onClick={onBack} />
      </div>
    );
  const filtered = segments.filter((s) =>
    `${s[1] ?? s.speaker} ${s[2] ?? s.text}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const ask = async () => {
    try {
      setAnswer(
        await api.ask(
          "apollo-demo",
          question || "What were the key decisions?",
        ),
      );
    } catch (e) {
      setAnswer({
        answer: e instanceof Error ? e.message : "Unable to answer",
        confidence: 0,
        evidence: [],
      });
    }
  };
  const compare = async () => {
    if (!compareId || !meeting) return;
    try {
      setComparison(await api.compare(meeting.id, compareId));
    } catch (e) {
      setComparison({
        error: e instanceof Error ? e.message : "Unable to compare meetings",
      });
    }
  };
  return (
    <div className="page meeting-page">
      <button className="back-btn" onClick={onBack}>
        ← Back
      </button>
      <div className="meeting-hero">
        <div>
          <div className="demo-label">
            <span /> {meeting.is_demo ? "DEMO DATA · " : ""}EVIDENCE-LINKED
            ANALYSIS
          </div>
          <h1>{meeting.title}</h1>
          <p>
            <Clock3 size={14} /> {meeting.status} <i /> <Users size={14} />{" "}
            persisted meeting
          </p>
        </div>
        <div className="top-actions">
          <a
            className="outline"
            href={api.exportUrl(meeting.id, "txt")}
            download
          >
            <FileText size={16} /> TXT
          </a>
          <a
            className="outline"
            href={api.exportUrl(meeting.id, "json")}
            download
          >
            JSON
          </a>
        </div>
      </div>
      <div className="tabs">
        {[
          "Overview",
          "Transcript",
          "Decisions",
          "Risks",
          "Ask meeting",
          "Compare",
        ].map((t) => (
          <button
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
            key={t}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "Compare" ? (
        <section className="panel compare-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">DECISION DRIFT</p>
              <h2>What changed?</h2>
            </div>
          </div>
          <p className="muted">
            Compare this meeting with another authorized meeting. Only persisted
            records are compared.
          </p>
          <select
            value={compareId}
            onChange={(e) => setCompareId(e.target.value)}
            style={{
              padding: 10,
              border: "1px solid var(--line)",
              borderRadius: 8,
              background: "var(--panel)",
              color: "var(--ink)",
              marginRight: 8,
            }}
          >
            <option value="">Choose a meeting</option>
            {meetings
              .filter((item) => item.id !== meeting.id)
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
          </select>
          <button className="primary" onClick={compare}>
            Compare
          </button>
          {comparison?.error && (
            <p className="api-notice">{comparison.error}</p>
          )}
          {comparison && !comparison.error && (
            <div className="insight-grid" style={{ marginTop: 20 }}>
              {(["decisions", "actions", "risks"] as const).map((key) => (
                <section className="panel" key={key}>
                  <p className="eyebrow">{key.toUpperCase()}</p>
                  <h3>New · {comparison[key].new.length}</h3>
                  <p className="muted">
                    {comparison[key].new.join(", ") || "None"}
                  </p>
                  <h3>Removed · {comparison[key].removed.length}</h3>
                  <p className="muted">
                    {comparison[key].removed.join(", ") || "None"}
                  </p>
                  <h3>Unchanged · {comparison[key].unchanged.length}</h3>
                </section>
              ))}
            </div>
          )}
        </section>
      ) : tab === "Ask meeting" ? (
        <section className="ask-layout">
          <div className="ask-box">
            <div className="ask-spark">
              <Sparkles size={22} />
            </div>
            <p className="eyebrow">MEETMIND COPILOT</p>
            <h2>Ask anything about this meeting.</h2>
            <div className="ask-input">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="What did we decide about deployment?"
              />
              <button className="primary" onClick={ask}>
                <ArrowUpRight size={17} />
              </button>
            </div>
          </div>
          {answer && (
            <div className="answer panel">
              <div className="answer-head">
                <span className="ai-badge">
                  <Sparkles size={14} /> GROUNDED ANSWER
                </span>
                <span>{Math.round(answer.confidence * 100)}% confidence</span>
              </div>
              <h3>{answer.answer}</h3>
              {answer.evidence.map((e, i) => (
                <div className="evidence" key={i}>
                  <strong>
                    Evidence · {e.timestamp} · {e.speaker}
                  </strong>
                  <p>{e.text || "Source record available."}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      ) : (
        <div className="content-grid">
          <section className="panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">EVIDENCE EXPLORER</p>
                <h2>Transcript</h2>
              </div>
              <div className="transcript-search">
                <Search size={15} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search transcript"
                />
              </div>
            </div>
            <div className="segments">
              {filtered.map((s, i) => {
                const timestamp = Array.isArray(s) ? s[0] : s.timestamp;
                const speaker = Array.isArray(s) ? s[1] : s.speaker;
                const text = Array.isArray(s) ? s[2] : s.text;
                const topic = Array.isArray(s) ? s[3] : s.topic;
                return (
                  <div className="segment" key={`${timestamp}-${i}`}>
                    <time>{timestamp}</time>
                    <div className="segment-line">
                      <div className="speaker-dot">
                        {speaker
                          .split(" ")
                          .map((x) => x[0])
                          .join("")}
                      </div>
                      <div>
                        <div className="speaker">
                          <strong>{speaker}</strong>
                          <span>{topic}</span>
                        </div>
                        <p>{text}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
          <section className="side-stack">
            <section className="panel">
              <div className="panel-head">
                <h2>Decisions</h2>
                <span className="count">3</span>
              </div>
              <Decision title="PostgreSQL for reporting" source="12:41" />
              <Decision title="Friday beta deployment" source="28:15" />
              <Decision title="Wednesday readiness review" source="28:15" />
            </section>
            <section className="panel risk-panel">
              <div className="panel-head">
                <h2>Risk radar</h2>
                <span className="severity">2 open</span>
              </div>
              <div className="risk">
                <span className="risk-bar high" />
                <div>
                  <strong>Security approval pending</strong>
                  <p>High · evidence at 23:17</p>
                </div>
              </div>
              <div className="risk">
                <span className="risk-bar medium" />
                <div>
                  <strong>Data residency unresolved</strong>
                  <p>Medium · evidence at 31:04</p>
                </div>
              </div>
            </section>
          </section>
        </div>
      )}
    </div>
  );
}
function Decision({ title, source }: { title: string; source: string }) {
  return (
    <div className="decision">
      <div className="decision-check">
        <CheckCircle2 size={15} />
      </div>
      <div>
        <strong>{title}</strong>
        <p>
          Confirmed · <span>{source}</span>
        </p>
      </div>
    </div>
  );
}
function Actions({
  actions,
  setActions,
}: {
  actions: ApiAction[];
  setActions: (v: ApiAction[]) => void;
}) {
  const complete = async (a: ApiAction) => {
    try {
      const updated = await api.updateAction(a.id, { status: "Completed" });
      setActions(actions.map((x) => (x.id === a.id ? updated : x)));
    } catch {}
  };
  return (
    <div className="page">
      <section className="welcome">
        <div>
          <p className="eyebrow">ACTION CENTER</p>
          <h1>
            Turn insight into <span>momentum.</span>
          </h1>
          <p className="lead">
            Persisted actions from your authorized meetings.
          </p>
        </div>
      </section>
      <section className="panel actions-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">ALL WORKSPACE ACTIONS</p>
            <h2>Action center</h2>
          </div>
          <div className="filter">
            <Filter size={15} /> Persisted
          </div>
        </div>
        <div className="action-table">
          <div className="action-head">
            <span>Task</span>
            <span>Meeting</span>
            <span>Owner</span>
            <span>Due</span>
            <span>Status</span>
          </div>
          {actions.map((a) => (
            <div className="action-row" key={a.id}>
              <div className="task">
                <span className={`priority ${a.priority.toLowerCase()}`} />
                <strong>{a.task}</strong>
              </div>
              <span className="muted">Meeting</span>
              <span>{a.owner}</span>
              <span>{a.deadline}</span>
              <button
                className={`pill ${a.status.toLowerCase().replace(" ", "-")}`}
                onClick={() => a.status !== "Completed" && complete(a)}
              >
                {a.status}
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
function Room({
  onBack,
  onDone,
}: {
  onBack: () => void;
  onDone: (meeting: ApiMeeting) => void;
}) {
  const [title, setTitle] = useState("Live meeting");
  const [consent, setConsent] = useState(false);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [micOn, setMicOn] = useState(true);
  const [cameraOn, setCameraOn] = useState(true);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState("");
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const meetingRef = useRef<ApiMeeting | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const startedAtRef = useRef(0);

  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - startedAtRef.current) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [recording]);

  useEffect(() => {
    return () =>
      streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  const start = async () => {
    if (!title.trim() || !consent) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setMessage("This browser does not support local camera recording.");
      return;
    }
    setBusy(true);
    setMessage("Requesting camera and microphone access...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: true,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => undefined);
      }
      const meeting = await api.createMeeting(title.trim());
      await api.join(meeting.id);
      await api.start(meeting.id);
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.start(1000);
      recorderRef.current = recorder;
      startedAtRef.current = Date.now();
      setElapsed(0);
      setRecording(true);
      setMessage(
        "Recording locally in this browser. You can stop at any time.",
      );
      meetingRef.current = meeting;
    } catch (e) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      setMessage(
        e instanceof Error ? e.message : "Unable to start the meeting room.",
      );
    } finally {
      setBusy(false);
    }
  };

  const stop = async () => {
    const meeting = meetingRef.current;
    const recorder = recorderRef.current;
    if (!meeting || !recorder) return;
    setBusy(true);
    setRecording(false);
    setMessage("Saving recording and preparing the meeting...");
    try {
      await new Promise<void>((resolve) => {
        recorder.onstop = () => resolve();
        recorder.stop();
      });
      const blob = new Blob(chunksRef.current, {
        type: recorder.mimeType || "video/webm",
      });
      const file = new File([blob], `${title.trim() || "meeting"}.webm`, {
        type: blob.type,
      });
      await api.upload(meeting.id, file);
      await api.end(meeting.id);
      await api.process(meeting.id);
      const saved = await api.getMeeting(meeting.id);
      onDone(saved);
    } catch (e) {
      setMessage(
        e instanceof Error ? e.message : "Unable to save the recording.",
      );
    } finally {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      recorderRef.current = null;
      meetingRef.current = null;
      setBusy(false);
    }
  };

  const toggleMic = () => {
    const next = !micOn;
    streamRef.current
      ?.getAudioTracks()
      .forEach((track) => (track.enabled = next));
    setMicOn(next);
  };
  const toggleCamera = () => {
    const next = !cameraOn;
    streamRef.current
      ?.getVideoTracks()
      .forEach((track) => (track.enabled = next));
    setCameraOn(next);
  };
  const time = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;

  return (
    <div className="page">
      <button
        className="back-btn"
        onClick={onBack}
        disabled={busy || recording}
      >
        ← Back to overview
      </button>
      <section className="welcome">
        <div>
          <p className="eyebrow">MEETMIND MEETING ROOM</p>
          <h1>Capture the conversation.</h1>
          <p className="lead">
            A local browser recording is saved to a persisted meeting when you
            stop.
          </p>
        </div>
        {recording && (
          <span className="live-tag">
            <i /> {time}
          </span>
        )}
      </section>
      <section className="panel room-panel">
        <div className="room-video-wrap">
          <video ref={videoRef} muted playsInline className="room-video" />
          {!recording && (
            <div className="room-placeholder">
              <Camera size={30} />
              <span>Camera preview appears after you start</span>
            </div>
          )}
        </div>
        {!recording && (
          <div className="room-setup">
            <label className="eyebrow">
              MEETING TITLE
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                disabled={busy}
              />
            </label>
            <label className="room-consent">
              <input
                type="checkbox"
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
                disabled={busy}
              />
              I consent to capture camera and microphone in this browser.
            </label>
            <button
              className="primary"
              onClick={start}
              disabled={busy || !consent || !title.trim()}
            >
              <Camera size={16} /> {busy ? "Starting..." : "Start recording"}
            </button>
          </div>
        )}
        {recording && (
          <div className="room-controls">
            <button
              className="icon-btn"
              onClick={toggleMic}
              title={micOn ? "Mute microphone" : "Unmute microphone"}
            >
              {micOn ? <Mic /> : <MicOff />}
            </button>
            <button
              className="icon-btn"
              onClick={toggleCamera}
              title={cameraOn ? "Turn camera off" : "Turn camera on"}
            >
              {cameraOn ? <Camera /> : <CameraOff />}
            </button>
            <button
              className="primary stop-recording"
              onClick={stop}
              disabled={busy}
            >
              <Square size={14} /> {busy ? "Saving..." : "Stop and save"}
            </button>
          </div>
        )}
        {message && <p className="muted room-message">{message}</p>}
        <p className="room-note">
          This room captures one local browser participant. Multi-user WebRTC,
          TURN, live captions, and external transcription require provider
          configuration.
        </p>
      </section>
    </div>
  );
}

function NewMeeting({
  onBack,
  onDone,
}: {
  onBack: () => void;
  onDone: (meeting: ApiMeeting) => void;
}) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const submit = async () => {
    if (!title.trim() || !file) return;
    setBusy(true);
    setMessage("Creating meeting and storing transcript...");
    try {
      const meeting = await api.createMeeting(title);
      await api.upload(meeting.id, file);
      onDone(meeting);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Unable to create meeting.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="page new-page">
      <button className="back-btn" onClick={onBack}>
        ← Back to overview
      </button>
      <div className="new-heading">
        <p className="eyebrow">NEW MEETING</p>
        <h1>
          Bring the conversation.
          <br />
          <span>We’ll find the signal.</span>
        </h1>
        <p>
          Upload a transcript for a real persisted meeting record, or configure
          a media transcription provider.
        </p>
      </div>
      <section className="panel" style={{ maxWidth: 620, margin: "35px auto" }}>
        <label className="eyebrow">
          MEETING TITLE
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Sprint planning"
            style={{
              display: "block",
              width: "100%",
              marginTop: 8,
              padding: 12,
              border: "1px solid var(--line)",
              borderRadius: 8,
              background: "transparent",
              color: "inherit",
            }}
          />
        </label>
        <input
          ref={input}
          type="file"
          accept=".txt,.srt,.vtt,audio/*,video/*"
          hidden
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <button
          className="upload-card"
          style={{ width: "100%", marginTop: 18 }}
          onClick={() => input.current?.click()}
        >
          <div className="upload-icon">
            <FileText size={25} />
          </div>
          <h2>{file ? file.name : "Choose a transcript or recording"}</h2>
          <p>
            TXT, SRT, VTT are parsed into evidence segments. Audio/video storage
            is supported; transcription requires configuration.
          </p>
        </button>
        {message && <p className="muted">{message}</p>}
        <button
          className="primary"
          style={{ marginTop: 18 }}
          disabled={busy || !title || !file}
          onClick={submit}
        >
          {busy ? "Processing…" : "Create and process meeting"}{" "}
          <ArrowUpRight size={16} />
        </button>
      </section>
    </div>
  );
}
function SearchPage({ onOpen }: { onOpen: (m?: ApiMeeting | null) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<
    Array<{ title: string; matched: string; timestamp?: string; type: string }>
  >([]);
  const search = async () => {
    if (query.length < 2) return;
    try {
      setResults((await api.search(query)).items);
    } catch {
      setResults([]);
    }
  };
  return (
    <div className="page">
      <section className="welcome">
        <div>
          <p className="eyebrow">MEETING MEMORY</p>
          <h1>Find the signal.</h1>
          <p className="lead">
            Search authorized meetings, transcript evidence, and actions.
          </p>
        </div>
      </section>
      <section className="panel">
        <div className="ask-input">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="Search for payment API, deployment, or a decision"
          />
          <button className="primary" onClick={search}>
            <Search size={16} />
          </button>
        </div>
        {results.map((r, i) => (
          <button className="meeting-row" key={i} onClick={() => onOpen()}>
            <div className="meeting-icon violet">
              <Search size={18} />
            </div>
            <div className="meeting-name">
              <strong>{r.matched}</strong>
              <span>
                {r.type} · {r.timestamp || "meeting memory"}
              </span>
            </div>
            <ChevronRight size={16} />
          </button>
        ))}
      </section>
    </div>
  );
}
function Empty({ onClick }: { onClick: () => void }) {
  return (
    <div className="panel">
      <h2>No meeting selected</h2>
      <p className="muted">Create or open a meeting to continue.</p>
      <button className="primary" onClick={onClick}>
        Back to overview
      </button>
    </div>
  );
}
