"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, clearToken, getToken, type DataSource, type SessionResponse } from "@/lib/api";
import type { Decision, Finding, Option, Question, ResearchResult, UserIntent } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";

type Step = "data" | "problem" | "research" | "options" | "decision";

function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

const STEPS: { id: Step; label: string }[] = [
  { id: "data", label: "Data" },
  { id: "problem", label: "Problem" },
  { id: "research", label: "Research" },
  { id: "options", label: "Options" },
  { id: "decision", label: "Decision" },
];

function stepFromStatus(status: string): Step {
  switch (status) {
    case "data_loaded":
    case "needs_input":
    case "understood":
      return "problem";
    case "researched":
      return "research";
    case "options_ready":
      return "options";
    case "decided":
    case "deck_ready":
      return "decision";
    default:
      return "data";
  }
}

export default function DashboardPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("data");
  const [sessionId, setSessionId] = useState<string>("");
  const [dataStatus, setDataStatus] = useState<string>("");
  const [dataSource, setDataSource] = useState<DataSource | null>(null);
  const [problemText, setProblemText] = useState("");
  const [intent, setIntent] = useState<UserIntent | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [research, setResearch] = useState<ResearchResult | null>(null);
  const [options, setOptions] = useState<Option[]>([]);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [ratings, setRatings] = useState<Record<string, Record<string, number>>>({});
  const [useAi, setUseAi] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState("");
  const [error, setError] = useState("");
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [scrapeSelector, setScrapeSelector] = useState("table tr");

  function startNewSession() {
    api.createSession()
      .then((s) => {
        setSessionId(s.id);
        localStorage.setItem("bdauth_session", s.id);
      })
      .catch((e) => setError(e.message));
  }

  function restoreSession(s: SessionResponse) {
    setSessionId(s.id);
    localStorage.setItem("bdauth_session", s.id);
    setDataStatus(s.status === "created" ? "" : "data_loaded");
    setDataSource(s.profile?.source ?? null);
    setProblemText(s.user_text || "");
    if (s.intent) setIntent(s.intent);
    if (s.research) setResearch(s.research);
    if (s.options?.length) setOptions(s.options);
    if (s.confidence) {
      setDecision({
        status: s.status,
        problem_type: s.problem_type || "improve",
        user_intent: s.intent ?? null,
        options: s.options ?? [],
        best: s.best ?? 0,
        reason: s.reason ?? "",
        confidence: s.confidence,
        why_not: s.check?.why_not ?? {},
        tie: s.check?.tie ?? false,
        evidence_strength: s.check?.evidence_strength ?? 0,
        findings: [],
      });
    }
    setStep(stepFromStatus(s.status));
    if (s.status === "needs_input") {
      api.submitProblem(s.id, s.user_text || "")
        .then((res) => {
          if (res.status === "needs_input") setQuestions(res.questions || []);
        })
        .catch(() => {});
    }
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    const saved = localStorage.getItem("bdauth_session");
    if (saved) {
      api.getSession(saved)
        .then(restoreSession)
        .catch(() => {
          localStorage.removeItem("bdauth_session");
          startNewSession();
        });
    } else {
      startNewSession();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  function logout() {
    localStorage.removeItem("bdauth_session");
    clearToken();
    router.replace("/login");
  }

  function newSession() {
    localStorage.removeItem("bdauth_session");
    setSessionId("");
    setDataStatus("");
    setDataSource(null);
    setProblemText("");
    setIntent(null);
    setQuestions([]);
    setAnswers({});
    setResearch(null);
    setOptions([]);
    setDecision(null);
    setStep("data");
    startNewSession();
  }

  async function run(label: string, fn: () => Promise<unknown>) {
    setLoading(true);
    setLoadingLabel(label);
    setError("");
    try {
      await fn();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
      setLoadingLabel("");
    }
  }

  async function uploadFile(file: File) {
    await run("Uploading data…", async () => {
      const s = await api.uploadData(sessionId, file);
      setDataStatus(s.status);
      setDataSource(s.profile?.source ?? null);
      setStep("problem");
    });
  }

  async function scrapePage() {
    await run("Scraping page…", async () => {
      const s = await api.scrape(sessionId, scrapeUrl, scrapeSelector);
      setDataStatus(s.status);
      setDataSource(s.profile?.source ?? null);
      setStep("problem");
    });
  }

  async function removeData() {
    await run("Removing data…", async () => {
      await api.removeData(sessionId);
      setDataStatus("");
      setDataSource(null);
      setProblemText("");
      setIntent(null);
      setStep("data");
    });
  }

  async function submitProblem() {
    await run("Understanding the problem…", async () => {
      const res = await api.submitProblem(sessionId, problemText);
      if (res.status === "needs_input") {
        setQuestions(res.questions || []);
        return;
      }
      setIntent(res.user_intent ?? null);
    });
  }

  async function answerAndContinue() {
    await run("Checking answers…", async () => {
      const res = await api.answerQuestions(sessionId, answers);
      if (res.status === "needs_input") {
        setQuestions(res.questions || []);
        return;
      }
      setIntent(res.user_intent ?? null);
    });
  }

  async function confirmIntent() {
    await run("Confirming understanding…", async () => {
      const res = await api.confirm(sessionId, {
        problem: intent?.problem || problemText,
        goal: intent?.goal || "reduce",
        metric: intent?.metric || "",
        group: intent?.group || "",
      });
      setIntent(res.user_intent ?? null);
      setStep("research");
    });
  }

  async function runResearch() {
    await run("Researching the web…", async () => {
      const res = await api.runResearch(sessionId);
      setResearch(res);
    });
  }

  async function generateOptions() {
    await run("Generating options…", async () => {
      const res = await api.generateOptions(sessionId, useAi);
      setOptions(res.options || []);
      const initial: Record<string, Record<string, number>> = {};
      (res.options || []).forEach((o, i) => {
        initial[String(i)] = { impact: o.impact, cost: o.cost, risk: o.risk, speed: o.speed };
      });
      setRatings(initial);
      setStep("options");
    });
  }

  async function updateRatings() {
    await run("Scoring options…", async () => {
      const res = await api.updateRatings(sessionId, ratings);
      setOptions(res.options || []);
      const d = await api.getDecision(sessionId);
      setDecision(d);
      setStep("decision");
    });
  }

  async function downloadDeck() {
    await run("Building deck…", async () => {
      await api.buildDeck(sessionId);
    });
    const url = api.getDeckUrl(sessionId);
    const token = getToken();
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    const blob = await res.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "briefing.pptx";
    link.click();
  }

  const best = decision ? decision.options[decision.best] : null;
  const loadingFor = (label: string) => loading && loadingLabel === label;

  return (
    <main className="min-h-screen p-6">
      <header className="mx-auto mb-6 flex max-w-5xl items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Briefing Deck Agent</h1>
          <p className="text-sm text-muted-foreground">Data → problem → research → options → decision</p>
        </div>
        <Button variant="outline" onClick={newSession}>New session</Button>
        <Button variant="outline" onClick={logout}>Sign out</Button>
      </header>

      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex flex-wrap gap-2">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center gap-2">
              <button
                onClick={() => setStep(s.id)}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  step === s.id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-accent"
                }`}
              >
                {i + 1}. {s.label}
              </button>
              {i < STEPS.length - 1 && <span className="text-muted-foreground">→</span>}
            </div>
          ))}
        </div>

        {error && <div className="mb-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        {loading && (
          <div className="mb-4 flex items-center gap-2 rounded-md border bg-muted p-3 text-sm">
            <Spinner className="h-4 w-4" />
            <span>{loadingLabel || "Loading…"}</span>
          </div>
        )}

        {step === "data" && (
          <div className="space-y-4">
            {dataStatus && (
              <Card>
                <CardContent className="flex items-center justify-between gap-4 p-4">
                  <div>
                    <p className="text-sm font-medium">Data loaded</p>
                    <p className="text-xs text-muted-foreground">
                      {dataSource?.type === "upload" && `File: ${String(dataSource.filename)}`}
                      {dataSource?.type === "scrape" &&
                        `Scraped: ${String(dataSource.url)} (${String(dataSource.selector)})`}
                    </p>
                  </div>
                  <Button variant="outline" onClick={removeData} disabled={loading}>
                    {loadingFor("Removing data…") ? "Removing…" : "Remove data"}
                  </Button>
                </CardContent>
              </Card>
            )}
            <Card>
              <CardHeader><CardTitle>Load your data</CardTitle></CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="file">Upload CSV, Excel or JSON</Label>
                  <Input id="file" type="file" accept=".csv,.xlsx,.xls,.json" disabled={loading}
                    onChange={(e) => e.target.files?.[0] && uploadFile(e.target.files[0])} />
                </div>
                <div className="flex items-center gap-3 text-sm text-muted-foreground"><span>or scrape a page</span></div>
                <div className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-[1fr_160px_auto]">
                    <Input placeholder="https://example.com" value={scrapeUrl}
                      onChange={(e) => setScrapeUrl(e.target.value)} />
                    <Input placeholder="table tr" value={scrapeSelector}
                      onChange={(e) => setScrapeSelector(e.target.value)} />
                    <Button variant="secondary" onClick={scrapePage} disabled={loading || !scrapeUrl}>
                      {loadingFor("Scraping page…") ? "Scraping…" : "Scrape"}
                    </Button>
                  </div>
                  <select
                    value={scrapeSelector}
                    onChange={(e) => setScrapeSelector(e.target.value)}
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                  >
                    <option value="table tr">Table rows — table tr</option>
                    <option value="h2">Section headings — h2</option>
                    <option value="li">Lists and cards — li</option>
                    <option value="p">Paragraphs — p</option>
                  </select>
                </div>
                {dataStatus && <Badge>{dataStatus}</Badge>}
              </CardContent>
            </Card>
          </div>
        )}

        {step === "problem" && (
          <Card>
            <CardHeader><CardTitle>Describe the problem</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="e.g. we pay too much overtime and HR needs a plan next month"
                value={problemText}
                onChange={(e) => setProblemText(e.target.value)}
                disabled={loading}
              />
              <div className="flex gap-2">
                <Button onClick={submitProblem} disabled={loading || !problemText.trim()}>
                  {loadingFor("Understanding the problem…") ? "Understanding…" : "Understand"}
                </Button>
                <Button variant="outline" onClick={() => setStep("data")}>Back</Button>
              </div>

              {questions.length > 0 && (
                <div className="space-y-3 rounded-md border p-4">
                  <p className="font-medium">Here is what I understood — please answer:</p>
                  {questions.map((q) => (
                    <div key={q.id} className="space-y-2">
                      <Label>{q.text}</Label>
                      {q.kind === "choice" && q.options ? (
                        <div className="flex flex-wrap gap-2">
                          {q.options.map((opt) => (
                            <Button key={opt} variant={answers[q.id] === opt ? "default" : "outline"} size="sm"
                              onClick={() => setAnswers({ ...answers, [q.id]: opt })}>{opt}</Button>
                          ))}
                        </div>
                      ) : (
                        <Input value={answers[q.id] || ""} onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })} />
                      )}
                    </div>
                  ))}
                  <Button onClick={answerAndContinue} disabled={loading || Object.keys(answers).length < questions.length}>
                    {loadingFor("Checking answers…") ? "Checking…" : "Continue"}
                  </Button>
                </div>
              )}

              {intent && (
                <div className="space-y-3 rounded-md border p-4">
                  <p className="font-medium">Here is what I understood</p>
                  <div className="grid gap-2 text-sm">
                    <div><span className="text-muted-foreground">Problem:</span> {intent.problem}</div>
                    <div><span className="text-muted-foreground">Goal:</span> {intent.goal}</div>
                    <div><span className="text-muted-foreground">Metric:</span> {intent.metric}</div>
                    <div><span className="text-muted-foreground">Group:</span> {intent.group}</div>
                  </div>
                  <Button onClick={confirmIntent} disabled={loading}>
                    {loadingFor("Confirming understanding…") ? "Confirming…" : "Confirm and continue"}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {step === "research" && (
          <Card>
            <CardHeader><CardTitle>External research</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Search the web for good practices, causes, benchmarks and risks. Queries use only the generic problem wording.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={runResearch} disabled={loading}>
                  {loadingFor("Researching the web…") ? "Researching…" : "Run research"}
                </Button>
                <Button variant="secondary" onClick={generateOptions} disabled={loading}>
                  {loadingFor("Generating options…") ? "Generating…" : "Skip and generate options"}
                </Button>
              </div>
              {research && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Badge>{research.status}</Badge>
                    <span>Coverage {Math.round((research.coverage || 0) * 100)}%</span>
                    <span>{research.findings?.length ?? 0} findings</span>
                    <span>{research.sources?.length ?? 0} sources</span>
                  </div>
                  <Progress value={Math.round((research.coverage || 0) * 100)} />
                  {loadingFor("Researching the web…") && <Progress value={40} />}
                  {research.message && <p className="text-sm text-amber-600">{research.message}</p>}
                  {research.page_errors && research.page_errors.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Skipped {research.page_errors.length} page(s): {research.page_errors.slice(0, 3).join(", ")}
                    </p>
                  )}
                  <Button onClick={generateOptions} disabled={loading}>
                    {loadingFor("Generating options…") ? "Generating…" : "Generate options"}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {step === "options" && (
          <Card>
            <CardHeader><CardTitle>Three solutions</CardTitle></CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-2">
                <input type="checkbox" id="useAi" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} />
                <Label htmlFor="useAi">Use AI for option wording (requires a key)</Label>
              </div>
              {options.map((o, i) => (
                <div key={o.name} className="space-y-3 rounded-md border p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium">{i + 1}. {o.name}</h3>
                    <Badge>score {o.score.toFixed(2)}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{o.summary}</p>
                  {(["impact", "cost", "risk", "speed"] as const).map((k) => (
                    <div key={k} className="grid grid-cols-[100px_1fr_40px] items-center gap-3 text-sm">
                      <Label className="capitalize">{k}</Label>
                      <Slider
                        value={[ratings[String(i)]?.[k] ?? o[k]]}
                        min={1} max={5} step={1}
                        onValueChange={(v) => setRatings((r) => ({ ...r, [String(i)]: { ...r[String(i)], [k]: v[0] } }))}
                      />
                      <span>{ratings[String(i)]?.[k] ?? o[k]}</span>
                    </div>
                  ))}
                </div>
              ))}
              <div className="flex gap-2">
                <Button onClick={updateRatings} disabled={loading || options.length === 0}>
                  {loadingFor("Scoring options…") ? "Scoring…" : "Update ratings and decide"}
                </Button>
                <Button variant="outline" onClick={() => setStep("research")}>Back</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {step === "decision" && decision && (
          <div className="space-y-6">
            <Card>
              <CardHeader><CardTitle>Recommendation</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {best && (
                  <div className="space-y-2">
                    <h3 className="text-xl font-semibold">{best.name}</h3>
                    <p className="text-sm">{best.idea}</p>
                    <p className="text-sm text-muted-foreground">{best.expected_effect}</p>
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  <Badge>{decision.confidence.label} confidence</Badge>
                  <Badge variant="outline">winner in {decision.confidence.wins}/{decision.confidence.total} scenarios</Badge>
                  <Badge variant="outline">{decision.confidence.evidence_strength} evidence</Badge>
                </div>
                <p className="text-sm">{decision.reason}</p>
                {decision.tie && <p className="text-sm font-medium text-amber-600">Human decision required: the top two options are tied.</p>}
                <Button onClick={downloadDeck} disabled={loading}>
                  {loadingFor("Building deck…") ? "Building…" : "Download briefing.pptx"}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Why not the others</CardTitle></CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {Object.entries(decision.why_not || {}).map(([i, text]) => (
                    <li key={i}>{text}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Comparison</CardTitle></CardHeader>
              <CardContent>
                <Table>
                  <TableHeader><TableRow>
                    <TableHead>Option</TableHead><TableHead>Impact</TableHead><TableHead>Cost</TableHead>
                    <TableHead>Risk</TableHead><TableHead>Speed</TableHead><TableHead>Score</TableHead>
                  </TableRow></TableHeader>
                  <TableBody>
                    {decision.options.map((o, i) => (
                      <TableRow key={o.name} className={i === decision.best ? "bg-primary/10" : ""}>
                        <TableCell>{o.name}</TableCell>
                        <TableCell>{o.impact}</TableCell>
                        <TableCell>{o.cost}</TableCell>
                        <TableCell>{o.risk}</TableCell>
                        <TableCell>{o.speed}</TableCell>
                        <TableCell>{o.score.toFixed(2)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </main>
  );
}
