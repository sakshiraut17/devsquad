/**
 * DevSquad Frontend Types matching backend Pydantic V2 models.
 */

export type RunStatus =
  | "QUEUED"
  | "INGESTING"
  | "PLANNING"
  | "CODING"
  | "SECURITY_SCANNING"
  | "TESTING"
  | "REVIEWING"
  | "AWAITING_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "CREATING_PR"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export interface User {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Repository {
  id: string;
  owner_id?: string | null;
  github_repository_id: number;
  full_name: string;
  default_branch: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Issue {
  id: string;
  repository_id: string;
  github_issue_number: number;
  title: string;
  body: string;
  state: string;
  labels: string[];
  html_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Run {
  id: string;
  repository_id: string;
  issue_id: string;
  status: RunStatus;
  current_node: string;
  retry_count: number;
  started_at?: string | null;
  finished_at?: string | null;
  error_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface EvidenceReference {
  file_path: string;
  start_line: number;
  end_line: number;
  file_sha256: string;
  base_commit_sha: string;
  repo_owner: string;
  repo_name: string;
  excerpt: string;
  symbol?: string | null;
  purpose: string;
}

export interface PlanStep {
  id: string;
  description: string;
  target_files: string[];
  rationale: string;
}

export interface StructuredPlan {
  objective: string;
  problem_summary: string;
  problem_interpretation?: string | null;
  root_cause_hypothesis?: string | null;
  steps: PlanStep[];
  acceptance_criteria: string[];
  required_tests: string[];
  risks: string[];
  assumptions: string[];
  uncertainties: string[];
  evidence_citations?: EvidenceReference[];
  target_files?: string[];
  regression_test_strategy?: string[];
  needs_additional_context?: boolean;
  additional_context_request?: string | null;
  declined_reason?: string | null;
  is_verified?: boolean;
}

export interface TestResult {
  status: string;
  environment: string;
  commands_executed: string[];
  exit_code: number;
  passed: number;
  failed: number;
  skipped: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
  error_message?: string | null;
}

export interface ReviewFinding {
  severity: "info" | "warning" | "critical" | "blocking";
  file_path: string;
  line_number?: number | null;
  description: string;
  suggested_fix?: string | null;
}

export interface ReviewResponse {
  findings: ReviewFinding[];
  acceptance_criteria_met: boolean;
  recommendation: "approve" | "request_changes" | "reject";
  unresolved_risks: string[];
}

export interface RepositoryContextSummary {
  repo_owner: string;
  repo_name: string;
  target_branch: string;
  base_commit_sha: string;
  retrieved_at: string;
  total_token_count: number;
  context_window_limit: number;
  truncation_applied: boolean;
  unranked_files_count: number;
  retrieval_limitations: string[];
  selected_files?: Record<string, {
    path: string;
    sha256: string;
    token_count: number;
    is_truncated: boolean;
    total_lines: number;
  }>;
}

export interface FailedPatchRecord {
  diff_hash: string;
  revision: number;
  failure_stage: string;
  failure_reason: string;
  created_at: string;
}

export interface WorkflowStateSnapshot {
  run_id: string;
  checkpoint_found: boolean;
  state?: {
    status?: RunStatus;
    current_stage?: string;
    patch_revision?: number;
    repair_attempts?: number;
    validation_status?: string;
    error_message?: string | null;
    plan?: StructuredPlan | null;
    security_result?: SecurityScanResult | null;
    test_result?: TestResult | null;
    review?: ReviewResponse | null;
    repository_context?: RepositoryContextSummary | null;
    failed_patch_registry?: FailedPatchRecord[] | null;
  };
}

export interface GitHubRemoteIssue {
  number: number;
  title: string;
  body?: string | null;
  state: string;
  labels: string[];
  html_url: string;
  author?: string | null;
  comments_count: number;
}

export interface AgentEvent {
  id: string;
  run_id: string;
  agent_name: string;
  event_type: string;
  message: string;
  input_summary?: string | null;
  output_summary?: string | null;
  duration_ms?: number | null;
  created_at: string;
}

export interface Patch {
  id: string;
  run_id: string;
  revision: number;
  unified_diff: string;
  target_files: string[];
  summary: string;
  content_hash: string;
  validation_status: string;
  created_at: string;
}

export interface ApprovalRecord {
  id: string;
  run_id: string;
  patch_id: string;
  approver_id?: string | null;
  decision: "approved" | "rejected";
  patch_hash: string;
  validation_evidence?: Record<string, unknown> | null;
  feedback?: string | null;
  created_at: string;
}

export type SubsystemStatus = "healthy" | "operational" | "degraded" | "unhealthy" | "unavailable" | "unconfigured" | "error";

export interface ComponentHealth {
  component?: string;
  name?: string;
  status: SubsystemStatus;
  message?: string;
  latency_ms?: number | null;
  details?: Record<string, unknown> | null;
}

export interface HealthResponse {
  status: SubsystemStatus;
  timestamp: string;
  version: string;
  environment?: string;
  components: Record<string, any>;
}

export interface OverviewStats {
  repositories_count: number;
  open_issues_count: number;
  total_runs_count: number;
  active_runs_count: number;
  awaiting_approval_count: number;
  failed_runs_count: number;
  completed_runs_count: number;
}

export type SecuritySeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type SecurityGateStatus = "PASSED" | "BLOCKED" | "UNVERIFIED";

export interface SecurityFinding {
  id?: string | null;
  run_id: string;
  patch_id?: string | null;
  patch_revision: number;
  patch_hash: string;
  base_commit_sha?: string | null;
  category: string;
  rule_id: string;
  title: string;
  description: string;
  severity: SecuritySeverity;
  confidence: string;
  file_path?: string | null;
  line_start?: number | null;
  line_end?: number | null;
  evidence_redacted?: string | null;
  remediation?: string | null;
  scanner_name: string;
  scanner_version?: string | null;
  advisory_id?: string | null;
  is_blocking: boolean;
  status: string;
  created_at?: string | null;
}

export interface SecuritySummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  total: number;
}

export interface SecurityScanResult {
  run_id: string;
  patch_id?: string | null;
  patch_revision?: number;
  patch_hash?: string;
  base_commit_sha?: string | null;
  status: SecurityGateStatus;
  can_approve: boolean;
  findings_count?: number;
  critical_count?: number;
  high_count?: number;
  medium_count?: number;
  low_count?: number;
  info_count?: number;
  block_reasons: string[];
  findings: SecurityFinding[];
  summary?: SecuritySummary;
  scanners_executed: string[];
  duration_ms?: number;
  scanned_at?: string;
}
