#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const BASE_URL = "https://app.sideshift.app/api/v1";
const API_KEY = process.env.SIDESHIFT_API_KEY;

if (!API_KEY) {
  process.stderr.write("Error: SIDESHIFT_API_KEY environment variable is required\n");
  process.exit(1);
}

async function sideshiftFetch(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "x-api-key": API_KEY,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`SideShift API error ${res.status}: ${text}`);
  }

  return res.json();
}

function buildQuery(params) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (!entries.length) return "";
  const qs = new URLSearchParams();
  for (const [k, v] of entries) {
    if (Array.isArray(v)) {
      for (const item of v) qs.append(k, item);
    } else {
      qs.set(k, String(v));
    }
  }
  return "?" + qs.toString();
}

const server = new McpServer({
  name: "sideshift",
  version: "1.0.0",
});

// ── Programs ──────────────────────────────────────────────────────────────────

server.tool(
  "list_programs",
  "List all campaigns/programs in SideShift. Returns id, name, description, status.",
  {
    page: z.number().int().min(1).default(1).optional().describe("Page number"),
    limit: z.number().int().min(1).max(100).default(25).optional().describe("Results per page"),
    status: z.enum(["draft", "active", "paused", "completed", "archived"]).optional().describe("Filter by status"),
    search: z.string().optional().describe("Search by program name"),
  },
  async ({ page, limit, status, search }) => {
    const data = await sideshiftFetch("/programs" + buildQuery({ page, limit, status, search }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

server.tool(
  "create_program_invite",
  "Generate a shareable invite link for a program so creators can join directly.",
  {
    programId: z.string().describe("Program ID (get from list_programs)"),
    expiresInDays: z.number().int().min(1).max(90).optional().nullable().describe("Days until link expires (omit for never)"),
    maxUses: z.number().int().min(1).optional().nullable().describe("Max times link can be used (omit for unlimited)"),
  },
  async ({ programId, expiresInDays, maxUses }) => {
    const data = await sideshiftFetch(`/programs/${programId}/invite`, {
      method: "POST",
      body: JSON.stringify({ expiresInDays, maxUses }),
    });
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

// ── Posts ─────────────────────────────────────────────────────────────────────

server.tool(
  "list_posts",
  "List creator posts with metrics (views, likes, comments, shares, earnings). Filter by program, platform, creator, or date range.",
  {
    page: z.number().int().default(1).optional(),
    limit: z.number().int().max(100).default(25).optional(),
    program: z.array(z.string()).optional().describe("Filter by program IDs"),
    platform: z.array(z.enum(["tiktok", "instagram", "youtube"])).optional().describe("Filter by platforms"),
    creator: z.array(z.string()).optional().describe("Filter by creator IDs"),
    fromDate: z.string().optional().describe("Filter from date (YYYY-MM-DD)"),
    toDate: z.string().optional().describe("Filter to date (YYYY-MM-DD)"),
  },
  async ({ page, limit, program, platform, creator, fromDate, toDate }) => {
    const data = await sideshiftFetch("/posts" + buildQuery({ page, limit, program, platform, creator, fromDate, toDate }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

server.tool(
  "get_post",
  "Get full details for a single post: metrics, payment status, contract info, creator info, bonuses.",
  {
    postId: z.string().describe("Post ID"),
  },
  async ({ postId }) => {
    const data = await sideshiftFetch(`/posts/${postId}`);
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

server.tool(
  "get_post_metrics_history",
  "Get daily metrics history for a post (views, likes, comments, shares, deltas, growth %).",
  {
    postId: z.string().describe("Post ID"),
    days: z.number().int().default(30).optional().describe("Days of history (0 = all)"),
    limit: z.number().int().max(500).default(100).optional().describe("Max data points"),
  },
  async ({ postId, days, limit }) => {
    const data = await sideshiftFetch(`/posts/${postId}/metrics-history` + buildQuery({ days, limit }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

// ── Analytics ─────────────────────────────────────────────────────────────────

server.tool(
  "get_kpis",
  "Get top-level KPIs: program counts by status, contract counts by status, total posts/views/likes/earnings, creator counts.",
  {},
  async () => {
    const data = await sideshiftFetch("/analytics/kpis");
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

server.tool(
  "get_analytics_overview",
  "Get the full analytics overview: summary metrics, top 10 posts, top 10 creators, platform breakdown. Matches the /overall dashboard page.",
  {
    programId: z.string().optional().describe("Filter by program"),
    creatorId: z.string().optional().describe("Filter by creator"),
    platform: z.enum(["tiktok", "instagram", "youtube"]).optional().describe("Filter by platform"),
    fromDate: z.string().optional().describe("Start date (YYYY-MM-DD)"),
    toDate: z.string().optional().describe("End date (YYYY-MM-DD)"),
  },
  async ({ programId, creatorId, platform, fromDate, toDate }) => {
    const data = await sideshiftFetch("/analytics/overview" + buildQuery({ programId, creatorId, platform, fromDate, toDate }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

server.tool(
  "get_analytics_videos",
  "List all tracked videos with full analytics, sorting (views, likes, engagement), and filtering. Includes summary totals.",
  {
    page: z.number().int().default(1).optional(),
    limit: z.number().int().max(100).default(50).optional(),
    sortBy: z.enum(["uploadedAt", "views", "likes", "engagement"]).default("views").optional(),
    sortOrder: z.enum(["asc", "desc"]).default("desc").optional(),
    program: z.array(z.string()).optional().describe("Filter by program IDs"),
    platform: z.array(z.enum(["tiktok", "instagram", "youtube"])).optional(),
    creator: z.array(z.string()).optional(),
    fromDate: z.string().optional().describe("YYYY-MM-DD"),
    toDate: z.string().optional().describe("YYYY-MM-DD"),
    minViews: z.number().int().optional().describe("Minimum view count"),
    paid: z.enum(["true", "false", "all"]).default("all").optional(),
  },
  async (params) => {
    const data = await sideshiftFetch("/analytics/videos" + buildQuery(params));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

server.tool(
  "get_analytics_accounts",
  "List all tracked creator accounts with aggregated stats per account (total views, posts, ER, earnings, etc.).",
  {
    page: z.number().int().default(1).optional(),
    limit: z.number().int().max(100).default(50).optional(),
    platform: z.string().optional().describe("Filter by platform"),
    programId: z.string().optional().describe("Filter by program"),
    sortBy: z.enum(["totalViews", "totalPosts", "engagementRate", "creator"]).default("totalViews").optional(),
    sortOrder: z.enum(["asc", "desc"]).default("desc").optional(),
  },
  async (params) => {
    const data = await sideshiftFetch("/analytics/accounts" + buildQuery(params));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

server.tool(
  "get_analytics_recruitment",
  "Get daily recruitment analytics: invites sent, responses received, response rate.",
  {
    fromDate: z.string().optional().describe("Start date YYYY-MM-DD (defaults to 29 days ago)"),
    toDate: z.string().optional().describe("End date YYYY-MM-DD (defaults to today)"),
  },
  async ({ fromDate, toDate }) => {
    const data = await sideshiftFetch("/analytics/recruitment" + buildQuery({ fromDate, toDate }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

// ── Payouts ───────────────────────────────────────────────────────────────────

server.tool(
  "list_payouts",
  "List wallet activity: all credits and debits (payouts to creators, adjustments, refunds).",
  {
    page: z.number().int().default(1).optional(),
    limit: z.number().int().max(100).default(25).optional(),
  },
  async ({ page, limit }) => {
    const data = await sideshiftFetch("/payouts" + buildQuery({ page, limit }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

server.tool(
  "list_pending_payouts",
  "List all payouts that are pending (not yet sent to creators).",
  {
    page: z.number().int().default(1).optional(),
    limit: z.number().int().max(100).default(25).optional(),
  },
  async ({ page, limit }) => {
    const data = await sideshiftFetch("/payouts/pending" + buildQuery({ page, limit }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

// ── Creators ──────────────────────────────────────────────────────────────────

server.tool(
  "list_creators",
  "List all creators on your SideShift roster with their profiles and stats.",
  {
    page: z.number().int().default(1).optional(),
    limit: z.number().int().max(100).default(25).optional(),
  },
  async ({ page, limit }) => {
    const data = await sideshiftFetch("/creators" + buildQuery({ page, limit }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

// ── Contracts ─────────────────────────────────────────────────────────────────

server.tool(
  "list_contracts",
  "List all creator contracts (active, pending, completed, etc.) with their terms and status.",
  {
    page: z.number().int().default(1).optional(),
    limit: z.number().int().max(100).default(25).optional(),
  },
  async ({ page, limit }) => {
    const data = await sideshiftFetch("/contracts" + buildQuery({ page, limit }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

// ── Invoices ──────────────────────────────────────────────────────────────────

server.tool(
  "list_invoices",
  "List all invoices sent to clients.",
  {
    page: z.number().int().default(1).optional(),
    limit: z.number().int().max(100).default(25).optional(),
  },
  async ({ page, limit }) => {
    const data = await sideshiftFetch("/invoices" + buildQuery({ page, limit }));
    return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
  }
);

// ── Start ─────────────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
