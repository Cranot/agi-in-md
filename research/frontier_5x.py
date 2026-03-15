#!/usr/bin/env python3
"""frontier_5x.py — Five frontier experiments in one run.

1. Factory-generated prisms vs hand-iterated champions
2. Compression breakpoints (80w/100w/120w)
3. Cross-language transfer (Go/TypeScript/larger Python)
4. Cross-prism breeding (hybrid cognitive operations)
5. Prism of Prisms (L12 on the prism portfolio itself)
"""
import concurrent.futures, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path
import threading

PRISM_DIR = Path("/home/claude/insights/prisms")
OUT = Path("/tmp/frontier_5x")
OUT.mkdir(exist_ok=True)

MAX_WORKERS = 4
ALL_RESULTS = {}
LOCK = threading.Lock()

# ── Helpers ─────────────────────────────────────────────────────────

def call_claude(system_prompt, user_input, model="haiku", timeout=180):
    """Run claude -p with system prompt file. Returns (text, cost, elapsed)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(system_prompt)
        sp_path = f.name
    env = {k: v for k, v in os.environ.items() if "CLAUDE" not in k.upper()}
    cmd = ["claude", "-p", "--tools", "", "--model", model,
           "--output-format", "json", "--system-prompt-file", sp_path]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, input=user_input, capture_output=True,
                          text=True, timeout=timeout, env=env)
        data = json.loads(r.stdout)
        text = data.get("result", "")
        cost = data.get("cost_usd", 0)
    except Exception as e:
        text, cost = f"FAILED: {e}", 0
    finally:
        try:
            os.unlink(sp_path)
        except:
            pass
    return text, cost, time.time() - t0


def strip_fm(text):
    """Strip YAML frontmatter."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text


def load_prism(name):
    """Load and strip frontmatter from prism file."""
    p = PRISM_DIR / f"{name}.md"
    return strip_fm(p.read_text()) if p.exists() else ""


def load_code(name):
    """Load a code target."""
    paths = {
        "starlette": "/home/claude/insights/real_code_starlette.py",
        "click": "/home/claude/insights/real_code_click.py",
        "tenacity": "/home/claude/insights/real_code_tenacity.py",
    }
    return Path(paths[name]).read_text() if name in paths else ""


SCORE_RUBRIC = (
    "You are scoring structural code analysis quality on a 1-10 scale.\n\n"
    "Score anchors:\n"
    "- 10: Conservation law with math form + line numbers + structural impossibility + actionable table\n"
    "- 9-9.5: Genuine structural properties, conservation law, specific locations, surprising findings, table\n"
    "- 8.5-9: Good structural depth, some invariant, specific enough to act on\n"
    "- 8-8.5: Solid with citations but conservation law generic or missing\n"
    "- 7-7.5: Standard code review - finds bugs, names patterns, no structural insight\n"
    "- 6 and below: Generic observations, no specific citations\n\n"
    "Output ONLY a single number (e.g., 8.5). Nothing else."
)


def score(text):
    """Score an analysis output using Haiku judge. Returns float or -1."""
    if not text or len(text) < 200 or "FAILED" in text[:50]:
        return -1.0
    scored = text[:5000]
    raw, _, _ = call_claude(SCORE_RUBRIC, f"## Analysis:\n\n{scored}", "haiku", 60)
    try:
        nums = re.findall(r"\b(\d+\.?\d*)\b", raw.strip())
        s = float(nums[0]) if nums else -1
        return s if 1 <= s <= 10 else -1
    except:
        return -1.0


def save(key, text):
    """Save output."""
    (OUT / f"{key}.txt").write_text(text or "EMPTY")


def save_prism(key, text):
    """Save a generated prism."""
    (OUT / f"{key}.md").write_text(text or "EMPTY")


# ── Embedded Code Targets ──────────────────────────────────────────

GO_ROUTER = r"""package router

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"sync"
)

type contextKey string
const userKey contextKey = "user"

type Middleware func(http.Handler) http.Handler

type Router struct {
	mu         sync.RWMutex
	routes     map[string]map[string]http.HandlerFunc
	middleware []Middleware
	notFound   http.HandlerFunc
}

func New() *Router {
	return &Router{routes: make(map[string]map[string]http.HandlerFunc)}
}

func (r *Router) Use(mw Middleware) { r.middleware = append(r.middleware, mw) }

func (r *Router) Handle(method, path string, h http.HandlerFunc) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.routes[path] == nil {
		r.routes[path] = make(map[string]http.HandlerFunc)
	}
	r.routes[path][method] = h
}

func (r *Router) Get(path string, h http.HandlerFunc)  { r.Handle("GET", path, h) }
func (r *Router) Post(path string, h http.HandlerFunc) { r.Handle("POST", path, h) }

func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	var handler http.Handler = http.HandlerFunc(r.dispatch)
	for i := len(r.middleware) - 1; i >= 0; i-- {
		handler = r.middleware[i](handler)
	}
	handler.ServeHTTP(w, req)
}

func (r *Router) dispatch(w http.ResponseWriter, req *http.Request) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	path := normalizePath(req.URL.Path)
	for pattern, methods := range r.routes {
		if params, ok := matchPath(pattern, path); ok {
			if h, exists := methods[req.Method]; exists {
				ctx := req.Context()
				for k, v := range params {
					ctx = context.WithValue(ctx, contextKey(k), v)
				}
				h(w, req.WithContext(ctx))
				return
			}
			http.Error(w, "Method Not Allowed", 405)
			return
		}
	}
	if r.notFound != nil {
		r.notFound(w, req)
	} else {
		http.NotFound(w, req)
	}
}

func normalizePath(p string) string {
	if p == "" { return "/" }
	if !strings.HasPrefix(p, "/") { p = "/" + p }
	if len(p) > 1 { p = strings.TrimRight(p, "/") }
	return p
}

func matchPath(pattern, path string) (map[string]string, bool) {
	pParts := strings.Split(pattern, "/")
	uParts := strings.Split(path, "/")
	if len(pParts) != len(uParts) { return nil, false }
	params := map[string]string{}
	for i, pp := range pParts {
		if strings.HasPrefix(pp, "{") && strings.HasSuffix(pp, "}") {
			params[pp[1:len(pp)-1]] = uParts[i]
		} else if pp != uParts[i] {
			return nil, false
		}
	}
	return params, true
}

func LoggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Printf("%s %s\n", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}

func RecoveryMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if err := recover(); err != nil {
				http.Error(w, "Internal Server Error", 500)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

func AuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		token := r.Header.Get("Authorization")
		if token == "" {
			http.Error(w, "Unauthorized", 401)
			return
		}
		user := validateToken(token)
		if user == "" {
			http.Error(w, "Forbidden", 403)
			return
		}
		ctx := context.WithValue(r.Context(), userKey, user)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func validateToken(token string) string {
	if strings.HasPrefix(token, "Bearer valid-") {
		return strings.TrimPrefix(token, "Bearer valid-")
	}
	return ""
}

type Group struct {
	router     *Router
	prefix     string
	middleware []Middleware
}

func (r *Router) Group(prefix string) *Group {
	return &Group{router: r, prefix: prefix}
}

func (g *Group) Use(mw Middleware) { g.middleware = append(g.middleware, mw) }

func (g *Group) Get(path string, h http.HandlerFunc) {
	wrapped := h
	for i := len(g.middleware) - 1; i >= 0; i-- {
		mw := g.middleware[i]
		next := wrapped
		wrapped = func(w http.ResponseWriter, r *http.Request) {
			mw(http.HandlerFunc(next)).ServeHTTP(w, r)
		}
	}
	g.router.Get(g.prefix+path, wrapped)
}

func GetUser(r *http.Request) string {
	if u, ok := r.Context().Value(userKey).(string); ok { return u }
	return ""
}

func Param(r *http.Request, name string) string {
	if v, ok := r.Context().Value(contextKey(name)).(string); ok { return v }
	return ""
}
"""

TS_MIDDLEWARE = r"""import { IncomingMessage, ServerResponse } from "http";

type Handler = (req: Request, res: Response, next: NextFn) => void | Promise<void>;
type NextFn = (err?: Error) => void;
type ErrorHandler = (err: Error, req: Request, res: Response, next: NextFn) => void;

interface Request extends IncomingMessage {
  params: Record<string, string>;
  body?: unknown;
  user?: { id: string; role: string };
  startTime?: number;
}

interface Response extends ServerResponse {
  json: (data: unknown) => void;
  status: (code: number) => Response;
}

interface Route {
  method: string;
  pattern: RegExp;
  paramNames: string[];
  handlers: Handler[];
}

class App {
  private routes: Route[] = [];
  private middleware: Handler[] = [];
  private errorHandlers: ErrorHandler[] = [];
  private settings: Record<string, unknown> = {};

  use(handler: Handler | ErrorHandler): void {
    if (handler.length === 4) {
      this.errorHandlers.push(handler as ErrorHandler);
    } else {
      this.middleware.push(handler as Handler);
    }
  }

  set(key: string, value: unknown): void { this.settings[key] = value; }
  getSetting(key: string): unknown { return this.settings[key]; }

  route(method: string, path: string, ...handlers: Handler[]): void {
    const paramNames: string[] = [];
    const pattern = new RegExp(
      "^" + path.replace(/:([^/]+)/g, (_, name) => {
        paramNames.push(name);
        return "([^/]+)";
      }) + "$"
    );
    this.routes.push({ method: method.toUpperCase(), pattern, paramNames, handlers });
  }

  get(path: string, ...h: Handler[]) { this.route("GET", path, ...h); }
  post(path: string, ...h: Handler[]) { this.route("POST", path, ...h); }

  async handle(req: Request, res: Response): Promise<void> {
    req.startTime = Date.now();
    req.params = {};
    this.augmentResponse(res);
    try {
      await this.runMiddleware(req, res, this.middleware);
      const route = this.findRoute(req);
      if (!route) {
        res.status(404).json({ error: "Not Found" });
        return;
      }
      Object.assign(req.params, route.params);
      await this.runMiddleware(req, res, route.route.handlers);
    } catch (err) {
      await this.handleError(err as Error, req, res);
    }
  }

  private augmentResponse(res: Response): void {
    res.json = (data: unknown) => {
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify(data));
    };
    res.status = (code: number) => { res.statusCode = code; return res; };
  }

  private findRoute(req: Request): { route: Route; params: Record<string, string> } | null {
    for (const route of this.routes) {
      if (route.method !== req.method) continue;
      const match = route.pattern.exec(req.url || "");
      if (match) {
        const params: Record<string, string> = {};
        route.paramNames.forEach((name, i) => { params[name] = match[i + 1]; });
        return { route, params };
      }
    }
    return null;
  }

  private runMiddleware(req: Request, res: Response, handlers: Handler[]): Promise<void> {
    return new Promise((resolve, reject) => {
      let idx = 0;
      const next: NextFn = (err?) => {
        if (err) return reject(err);
        if (idx >= handlers.length) return resolve();
        const handler = handlers[idx++];
        try {
          const result = handler(req, res, next);
          if (result && typeof (result as Promise<void>).catch === "function") {
            (result as Promise<void>).catch(next);
          }
        } catch (e) {
          reject(e);
        }
      };
      next();
    });
  }

  private async handleError(err: Error, req: Request, res: Response): Promise<void> {
    for (const handler of this.errorHandlers) {
      try {
        await new Promise<void>((resolve, reject) => {
          handler(err, req, res, (nextErr?) => nextErr ? reject(nextErr) : resolve());
        });
        return;
      } catch (nextErr) {
        err = nextErr as Error;
      }
    }
    res.status(500).json({ error: "Internal Server Error" });
  }
}

function logger(): Handler {
  return (req, res, next) => {
    const start = Date.now();
    res.on("finish", () => {
      console.log(`${req.method} ${req.url} ${res.statusCode} ${Date.now() - start}ms`);
    });
    next();
  };
}

function bodyParser(): Handler {
  return (req, res, next) => {
    if (req.method === "GET") return next();
    let data = "";
    req.on("data", (chunk: Buffer) => { data += chunk.toString(); });
    req.on("end", () => {
      try {
        req.body = data ? JSON.parse(data) : {};
      } catch {
        req.body = {};
      }
      next();
    });
    req.on("error", () => next());
  };
}

function auth(secret: string): Handler {
  return (req, res, next) => {
    const header = req.headers.authorization;
    if (!header || !header.startsWith("Bearer ")) {
      res.status(401).json({ error: "Unauthorized" });
      return;
    }
    const token = header.slice(7);
    if (token === secret) {
      req.user = { id: "system", role: "admin" };
    } else {
      req.user = { id: token, role: "user" };
    }
    next();
  };
}

function rateLimit(windowMs: number, max: number): Handler {
  const hits: Map<string, { count: number; resetTime: number }> = new Map();
  return (req, res, next) => {
    const key = req.headers["x-forwarded-for"] as string || req.socket.remoteAddress || "unknown";
    const now = Date.now();
    let record = hits.get(key);
    if (!record || now > record.resetTime) {
      record = { count: 0, resetTime: now + windowMs };
      hits.set(key, record);
    }
    record.count++;
    if (record.count > max) {
      res.status(429).json({ error: "Too Many Requests" });
      return;
    }
    next();
  };
}

export { App, Handler, Request, Response, logger, bodyParser, auth, rateLimit };
"""


# ── Experiment 1: Factory vs Champions ──────────────────────────────

FACTORY_COOK = (
    "Design a 3-step structural analysis lens (130-180 words) for the following analytical goal.\n\n"
    "Goal: {goal}\n\n"
    "Rules:\n"
    '- First line: "Execute every step below. Output the complete analysis."\n'
    "- Exactly 3 sections with ## Step 1/2/3 headers\n"
    "- Each step: one imperative sentence + 2-3 specific search patterns\n"
    "- Step 3 must require naming a conservation law or structural invariant\n"
    "- Step 3 must end with a | table | format\n"
    "- 130-180 words total\n"
    "- Must work on ANY codebase\n\n"
    "Output ONLY the lens text. No explanation, no fences."
)

GOALS = {
    "errors": "Find where failure information is destroyed. Trace corruption cascades through multiple hops to silent wrong results. Name the structural invariant.",
    "costs": "Find where performance data is hidden. Trace how hidden costs compound across call chains. Name the conservation law trading observability against performance.",
    "changes": "Find invisible coupling between components. Trace how a minimal change propagates through implicit dependencies. Name the coupling budget conservation law.",
    "promises": "Find where names lie about behavior. Classify each as narrowing, widening, or direction lie. Name the labeling debt conservation law.",
}
GOAL_TO_CHAMP = {
    "errors": "error_resilience", "costs": "optimize",
    "changes": "evolution", "promises": "api_surface",
}


def run_exp1():
    print("\n" + "=" * 60)
    print("  EXP 1: Factory vs Champions")
    print("=" * 60)
    starlette = load_code("starlette")
    results = {}

    def cook_and_run(goal_name):
        goal = GOALS[goal_name]
        champ_name = GOAL_TO_CHAMP[goal_name]
        # Cook factory prism
        factory_text, _, _ = call_claude(
            FACTORY_COOK.format(goal=goal), "Generate the lens now.",
            model="sonnet", timeout=120)
        if not factory_text or len(factory_text) < 100:
            return goal_name, {"factory": -1, "champion": -1}
        save_prism(f"factory_{goal_name}", factory_text)
        # Run factory on Starlette
        f_out, _, _ = call_claude(
            factory_text, f"Analyze this code.\n\n```python\n{starlette}\n```")
        save(f"exp1_factory_{goal_name}", f_out)
        # Run champion on Starlette
        champ_text = load_prism(champ_name)
        c_out, _, _ = call_claude(
            champ_text, f"Analyze this code.\n\n```python\n{starlette}\n```")
        save(f"exp1_champ_{goal_name}", c_out)
        # Score both
        f_score = score(f_out)
        c_score = score(c_out)
        return goal_name, {
            "factory": f_score, "champion": c_score,
            "factory_chars": len(f_out or ""), "champ_chars": len(c_out or ""),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(cook_and_run, g): g for g in GOALS}
        for f in concurrent.futures.as_completed(futs):
            name, data = f.result()
            results[name] = data
            fs, cs = data["factory"], data["champion"]
            delta = f"{fs - cs:+.1f}" if fs > 0 and cs > 0 else "?"
            print(f"  {name:12s} factory={fs:4.1f}  champ={cs:4.1f}  delta={delta}")

    ALL_RESULTS["exp1"] = results
    return results


# ── Experiment 2: Compression Breakpoints ───────────────────────────

COMPRESS_PROMPT = (
    "Compress this structural analysis lens to EXACTLY {target} words (+-10 words).\n\n"
    "Rules:\n"
    "- Keep exactly 3 ## Step sections\n"
    '- Keep "Execute every step below. Output the complete analysis." as first line\n'
    "- Keep ALL specific search patterns and nouns (active ingredients)\n"
    "- Cut: connective tissue, redundant elaboration, transition phrases\n"
    "- Keep Step 3 table format\n"
    "- Must still produce a conservation law\n\n"
    "LENS:\n{lens}\n\n"
    "Output ONLY the compressed lens text. Nothing else."
)


def run_exp2():
    print("\n" + "=" * 60)
    print("  EXP 2: Compression Breakpoints")
    print("=" * 60)
    starlette = load_code("starlette")
    prisms = {"error_resilience": 165, "optimize": 120, "evolution": 130, "api_surface": 130}
    targets = [80, 100, 120]
    results = {}

    def compress_and_run(name, target_w):
        original = load_prism(name)
        current_w = len(original.split())
        if current_w <= target_w + 10:
            return name, target_w, None
        compressed, _, _ = call_claude(
            COMPRESS_PROMPT.format(target=target_w, lens=original),
            "Compress now.", model="sonnet", timeout=120)
        if not compressed or len(compressed) < 50:
            return name, target_w, {"score": -1, "words": 0}
        save_prism(f"compress_{name}_{target_w}w", compressed)
        out, _, _ = call_claude(
            compressed, f"Analyze this code.\n\n```python\n{starlette}\n```")
        save(f"exp2_{name}_{target_w}w", out)
        s = score(out)
        return name, target_w, {
            "score": s, "words": len(compressed.split()), "chars": len(out or ""),
        }

    tasks = [(n, t) for n in prisms for t in targets]
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(compress_and_run, n, t) for n, t in tasks]
        for f in concurrent.futures.as_completed(futs):
            name, tw, data = f.result()
            if data is None:
                continue
            results.setdefault(name, {})[tw] = data
            print(f"  {name:20s} {tw}w -> score={data['score']:4.1f}  "
                  f"actual={data['words']}w  out={data.get('chars', 0)}c")

    ALL_RESULTS["exp2"] = results
    return results


# ── Experiment 3: Cross-Language Transfer ───────────────────────────

def run_exp3():
    print("\n" + "=" * 60)
    print("  EXP 3: Cross-Language Transfer")
    print("=" * 60)
    prism_names = ["error_resilience", "optimize", "evolution", "api_surface", "l12"]
    targets = {
        "go": ("```go\n" + GO_ROUTER + "\n```", "Go router"),
        "typescript": ("```typescript\n" + TS_MIDDLEWARE + "\n```", "TypeScript middleware"),
        "click": ("```python\n" + load_code("click") + "\n```", "Click (larger Python)"),
    }
    results = {}

    def run_one(prism_name, target_name):
        prism_text = load_prism(prism_name)
        code, desc = targets[target_name]
        out, _, _ = call_claude(
            prism_text, f"Analyze this {desc} code.\n\n{code}")
        save(f"exp3_{prism_name}_{target_name}", out)
        s = score(out)
        return prism_name, target_name, s, len(out or "")

    tasks = [(p, t) for p in prism_names for t in targets]
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(run_one, p, t) for p, t in tasks]
        for f in concurrent.futures.as_completed(futs):
            pn, tn, s, chars = f.result()
            results.setdefault(pn, {})[tn] = {"score": s, "chars": chars}
            print(f"  {pn:20s} x {tn:12s} -> {s:4.1f}  ({chars}c)")

    ALL_RESULTS["exp3"] = results
    return results


# ── Experiment 4: Cross-Prism Breeding ──────────────────────────────

BREED_PROMPT = (
    "Create ONE hybrid structural analysis lens by combining the cognitive operations "
    "of both parent lenses below. The hybrid must find things NEITHER parent finds "
    "alone - a genuine cross of their operations, not a union.\n\n"
    "PARENT A ({name_a}):\n{parent_a}\n\n"
    "PARENT B ({name_b}):\n{parent_b}\n\n"
    "Rules:\n"
    '- First line: "Execute every step below. Output the complete analysis."\n'
    "- Exactly 3 ## Step sections\n"
    "- Each step COMBINES operations from both parents in a novel way\n"
    "- Step 3 must name a conservation law and include a | table | format\n"
    "- 130-200 words total\n"
    "- Must work on any codebase\n\n"
    "Output ONLY the hybrid lens text. Nothing else."
)

HYBRIDS = [
    ("error_resilience", "evolution", "Error cascades through invisible handshakes"),
    ("optimize", "api_surface", "Hidden costs behind naming lies"),
    ("error_resilience", "optimize", "Error + performance info destruction"),
]


def run_exp4():
    print("\n" + "=" * 60)
    print("  EXP 4: Cross-Prism Breeding")
    print("=" * 60)
    starlette = load_code("starlette")
    results = {}

    def breed_and_run(a_name, b_name, desc):
        a_text = load_prism(a_name)
        b_text = load_prism(b_name)
        hybrid, _, _ = call_claude(
            BREED_PROMPT.format(
                name_a=a_name, parent_a=a_text,
                name_b=b_name, parent_b=b_text),
            f"Create hybrid for: {desc}", model="opus", timeout=300)
        if not hybrid or len(hybrid) < 80:
            return f"{a_name}+{b_name}", {"score": -1, "desc": desc}
        key = f"{a_name}_{b_name}"
        save_prism(f"hybrid_{key}", hybrid)
        out, _, _ = call_claude(
            hybrid, f"Analyze this code.\n\n```python\n{starlette}\n```")
        save(f"exp4_hybrid_{key}", out)
        s = score(out)
        return key, {
            "score": s, "chars": len(out or ""), "desc": desc,
            "hybrid_words": len(hybrid.split()),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(breed_and_run, a, b, d) for a, b, d in HYBRIDS]
        for f in concurrent.futures.as_completed(futs):
            key, data = f.result()
            results[key] = data
            print(f"  {key:30s} -> {data.get('score', -1):4.1f}  "
                  f"({data.get('chars', 0)}c)  [{data['desc']}]")

    ALL_RESULTS["exp4"] = results
    return results


# ── Experiment 5: Prism of Prisms ──────────────────────────────────

def run_exp5():
    print("\n" + "=" * 60)
    print("  EXP 5: Prism of Prisms")
    print("=" * 60)
    prism_names = ["error_resilience", "optimize", "evolution", "api_surface", "l12"]
    portfolio = "# Cognitive Prism Portfolio\n\n"
    portfolio += "Five prisms for structural code analysis. Each asks a different question.\n\n"
    for name in prism_names:
        text = load_prism(name)
        portfolio += f"## {name.upper()}\n\n{text}\n\n---\n\n"

    # Use L12 to analyze the prism portfolio
    l12 = load_prism("l12")
    out, _, _ = call_claude(l12, f"Analyze this system.\n\n{portfolio}", timeout=240)
    save("exp5_prism_of_prisms", out)
    s = score(out)

    results = {"score": s, "chars": len(out or "")}
    ALL_RESULTS["exp5"] = results
    print(f"  L12 on portfolio: score={s:4.1f}, {len(out or '')}c")
    if out and len(out) > 200:
        for line in out.split("\n"):
            ll = line.lower()
            if "conservation" in ll or "invariant" in ll or "law" in ll:
                print(f"  >> {line.strip()[:120]}")
                break
    return results


# ── Main ────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 60)
    print("  FRONTIER 5x - Five Experiments")
    print("=" * 60)

    # Run all 5 experiments in parallel threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        f1 = ex.submit(run_exp1)
        f2 = ex.submit(run_exp2)
        f3 = ex.submit(run_exp3)
        f4 = ex.submit(run_exp4)
        f5 = ex.submit(run_exp5)

        r1 = f1.result()
        r2 = f2.result()
        r3 = f3.result()
        r4 = f4.result()
        r5 = f5.result()

    elapsed = time.time() - t0

    # ── Final Report ──
    print("\n" + "=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)

    print("\n-- EXP 1: Factory vs Champions --")
    if r1:
        for g in ["errors", "costs", "changes", "promises"]:
            d = r1.get(g, {})
            fs, cs = d.get("factory", -1), d.get("champion", -1)
            delta = f"{fs - cs:+.1f}" if fs > 0 and cs > 0 else "?"
            print(f"  {g:12s}  factory={fs:4.1f}  champion={cs:4.1f}  delta={delta}")

    print("\n-- EXP 2: Compression Breakpoints --")
    if r2:
        print(f"  {'Prism':20s} {'80w':>6s} {'100w':>6s} {'120w':>6s}")
        for name in ["error_resilience", "optimize", "evolution", "api_surface"]:
            row = r2.get(name, {})
            vals = []
            for tw in [80, 100, 120]:
                d = row.get(tw)
                vals.append(f"{d['score']:4.1f}" if d and d["score"] > 0 else "  -  ")
            print(f"  {name:20s} {'  '.join(vals)}")

    print("\n-- EXP 3: Cross-Language Transfer --")
    if r3:
        print(f"  {'Prism':20s} {'Go':>6s} {'TS':>6s} {'Click':>6s}")
        for pn in ["error_resilience", "optimize", "evolution", "api_surface", "l12"]:
            row = r3.get(pn, {})
            vals = []
            for tn in ["go", "typescript", "click"]:
                d = row.get(tn)
                vals.append(f"{d['score']:4.1f}" if d and d["score"] > 0 else "  -  ")
            print(f"  {pn:20s} {'  '.join(vals)}")

    print("\n-- EXP 4: Cross-Prism Breeding --")
    if r4:
        for key, d in r4.items():
            print(f"  {key:30s} -> {d.get('score', -1):4.1f}  [{d.get('desc', '')}]")

    print("\n-- EXP 5: Prism of Prisms --")
    if r5:
        print(f"  Score: {r5.get('score', -1):.1f}, Output: {r5.get('chars', 0)} chars")

    print(f"\n  Total time: {elapsed:.0f}s")
    print(f"  All outputs: {OUT}/")

    # Save JSON
    with open(OUT / "results.json", "w") as f:
        json.dump(ALL_RESULTS, f, indent=2, default=str)
    print(f"  Results JSON: {OUT}/results.json")


if __name__ == "__main__":
    main()
