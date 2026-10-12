'use client';

import React, { useState } from 'react';
import {
  FolderGit2,
  AlertCircle,
  Search,
  Star,
  GitBranch,
  Layers,
  ChevronRight,
  FileCode,
  CheckCircle2,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import {
  fetchRepoInfo,
  fetchRepoIssues,
  fetchRepoTree,
  RepositoryData,
  IssueData,
  FileTreeNode,
} from '@/lib/api';

export const RepositorySelector: React.FC = () => {
  const [repoInput, setRepoInput] = useState<string>('sakshiraut17/devsquad');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [repoData, setRepoData] = useState<RepositoryData | null>(null);
  const [issues, setIssues] = useState<IssueData[]>([]);
  const [selectedIssue, setSelectedIssue] = useState<IssueData | null>(null);
  const [tree, setTree] = useState<FileTreeNode[]>([]);
  const [treeLoading, setTreeLoading] = useState<boolean>(false);

  const handleSearch = async (repoString?: string) => {
    const target = (repoString || repoInput).trim();
    if (!target.includes('/')) {
      setError('Please provide repository in "owner/repository" format (e.g., sakshiraut17/devsquad).');
      return;
    }

    const [owner, repo] = target.split('/');
    setLoading(true);
    setError(null);
    setSelectedIssue(null);
    setTree([]);

    try {
      const info = await fetchRepoInfo(owner, repo);
      if (!info) {
        setError(`Repository "${target}" could not be retrieved. Check repository name or network access.`);
        setRepoData(null);
        setIssues([]);
      } else {
        setRepoData(info);
        const issuesList = await fetchRepoIssues(owner, repo);
        setIssues(issuesList);
      }
    } catch (err: any) {
      setError(err?.message || 'An unexpected error occurred while querying GitHub API.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectIssue = async (issue: IssueData) => {
    setSelectedIssue(issue);
    if (!repoData) return;

    const [owner, repo] = repoData.full_name.split('/');
    setTreeLoading(true);
    try {
      const treeNodes = await fetchRepoTree(owner, repo);
      setTree(treeNodes.slice(0, 50)); // Show top files for context
    } catch (e) {
      console.error('Failed to load file tree:', e);
    } finally {
      setTreeLoading(false);
    }
  };

  return (
    <div className="bg-surface border border-border rounded-xl p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2 text-white font-bold text-lg">
            <FolderGit2 className="w-5 h-5 text-blue-400" />
            <span>Connected Repository & Issue Explorer</span>
          </div>
          <p className="text-xs text-muted mt-1">
            Retrieve real GitHub repository context, open issues, and codebase trees for automated resolution.
          </p>
        </div>

        {/* Quick Suggestion Pills */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted">Suggested:</span>
          {['sakshiraut17/devsquad', 'octocat/Hello-World'].map((sug) => (
            <button
              key={sug}
              onClick={() => {
                setRepoInput(sug);
                handleSearch(sug);
              }}
              className="px-2.5 py-1 rounded bg-card hover:bg-border text-gray-300 border border-border/80 transition-colors font-mono text-[11px]"
            >
              {sug}
            </button>
          ))}
        </div>
      </div>

      {/* Search Input Bar */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={repoInput}
            onChange={(e) => setRepoInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="owner/repo (e.g. sakshiraut17/devsquad)"
            className="w-full bg-card border border-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>
        <button
          onClick={() => handleSearch()}
          disabled={loading}
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          <span>{loading ? 'Fetching...' : 'Query GitHub'}</span>
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">GitHub Retrieval Notice</p>
            <p className="text-xs text-red-300 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Repository Metadata Card */}
      {repoData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-lg bg-card/60 border border-border/70 text-sm">
          <div>
            <span className="text-xs text-muted block mb-0.5">Repository</span>
            <span className="font-semibold text-white font-mono text-sm">{repoData.full_name}</span>
          </div>
          <div>
            <span className="text-xs text-muted block mb-0.5">Default Branch</span>
            <span className="text-white flex items-center gap-1">
              <GitBranch className="w-3.5 h-3.5 text-blue-400" />
              {repoData.default_branch}
            </span>
          </div>
          <div>
            <span className="text-xs text-muted block mb-0.5">Community</span>
            <span className="text-white flex items-center gap-1">
              <Star className="w-3.5 h-3.5 text-amber-400" />
              {repoData.stars_count} stars
            </span>
          </div>
          <div>
            <span className="text-xs text-muted block mb-0.5">Open Issues</span>
            <span className="text-white flex items-center gap-1 font-semibold text-emerald-400">
              <AlertCircle className="w-3.5 h-3.5 text-emerald-400" />
              {repoData.open_issues_count} open
            </span>
          </div>
        </div>
      )}

      {/* Two Column Section: Issues & Selected Context */}
      {repoData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
          {/* Column 1: Issues List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-white flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 text-emerald-400" />
                <span>Open Issues ({issues.length})</span>
              </h4>
              <span className="text-xs text-muted">Click an issue to inspect context</span>
            </div>

            {issues.length === 0 ? (
              <div className="p-8 text-center bg-card rounded-lg border border-border text-xs text-muted">
                No open issues currently found on this repository.
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {issues.map((issue) => {
                  const isSelected = selectedIssue?.issue_number === issue.issue_number;
                  return (
                    <div
                      key={issue.issue_number}
                      onClick={() => handleSelectIssue(issue)}
                      className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-blue-500/10 border-blue-500/60 shadow-md'
                          : 'bg-card border-border/80 hover:border-gray-600'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-bold text-blue-400">
                              #{issue.issue_number}
                            </span>
                            <h5 className="text-sm font-medium text-white leading-tight">
                              {issue.title}
                            </h5>
                          </div>
                          {issue.body && (
                            <p className="text-xs text-muted line-clamp-2 leading-relaxed">
                              {issue.body}
                            </p>
                          )}
                          {issue.labels.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {issue.labels.map((lb) => (
                                <span
                                  key={lb}
                                  className="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700"
                                >
                                  {lb}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <ChevronRight
                          className={`w-4 h-4 shrink-0 transition-transform ${
                            isSelected ? 'text-blue-400 translate-x-1' : 'text-gray-600'
                          }`}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Column 2: Selected Context & File Tree */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-white flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-purple-400" />
              <span>Issue Context & Target Codebase Tree</span>
            </h4>

            {selectedIssue ? (
              <div className="bg-card border border-border rounded-lg p-4 space-y-4">
                <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-md">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-blue-400 uppercase tracking-wide">
                      Selected Target
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Ready for AI Planner
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-white mt-1">
                    #{selectedIssue.issue_number}: {selectedIssue.title}
                  </h4>
                  <p className="text-xs text-gray-300 mt-1 whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto">
                    {selectedIssue.body || 'No description provided in issue body.'}
                  </p>
                </div>

                {/* File Tree Preview */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-muted flex items-center gap-1.5">
                      <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                      Repository File Structure ({tree.length} files parsed)
                    </span>
                    {treeLoading && <Loader2 className="w-3.5 h-3.5 animate-spin text-muted" />}
                  </div>

                  <div className="bg-[#0b0f19] border border-border/80 rounded-md p-3 max-h-52 overflow-y-auto font-mono text-xs text-gray-300 space-y-1">
                    {tree.length === 0 ? (
                      <span className="text-muted text-[11px]">Loading repository tree...</span>
                    ) : (
                      tree.map((node) => (
                        <div key={node.path} className="flex items-center justify-between hover:text-white py-0.5">
                          <span className="truncate">{node.path}</span>
                          <span className="text-[10px] text-muted shrink-0 ml-2">
                            {node.type === 'tree' ? 'DIR' : `${node.size || 0}B`}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-12 text-center bg-card rounded-lg border border-dashed border-border/80 text-xs text-muted flex flex-col items-center justify-center gap-2">
                <AlertCircle className="w-8 h-8 text-gray-600" />
                <span>Select an issue on the left to inspect its description and repository codebase tree.</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
