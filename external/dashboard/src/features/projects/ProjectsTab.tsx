import { useState, useEffect } from "react";
import { Folder, ChevronRight, ChevronDown, File, Plus } from "lucide-react";
import { StatusPill } from "../../components/common/StatusPill";
import type { FileNode, Project } from "../../types";
import { useQuery } from "@tanstack/react-query";
import { projectsApi } from "../../api/projects";

function FileTreeNode({ node, depth = 0 }: { node: FileNode; depth?: number }) {
  const [isExpanded, setIsExpanded] = useState(depth === 0);

  return (
    <div>
      <button
        onClick={() => node.type === "directory" && setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-2 py-1 hover:bg-slate-800/50 rounded text-sm transition"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {node.type === "directory" ? (
          <>
            {isExpanded ? (
              <ChevronDown className="w-3 h-3 text-slate-400" />
            ) : (
              <ChevronRight className="w-3 h-3 text-slate-400" />
            )}
            <Folder className="w-4 h-4 text-sheratan-accent" />
          </>
        ) : (
          <>
            <span className="w-3" />
            <File className="w-4 h-4 text-slate-500" />
          </>
        )}
        <span className="text-slate-300">{node.name}</span>
      </button>
      {node.type === "directory" && isExpanded && node.children && (
        <div>
          {node.children.map((child, i) => (
            <FileTreeNode key={i} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export function ProjectsTab() {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  const { data: projects = [], isLoading: isLoadingProjects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.getProjects(),
  });

  const { data: fileTree = [], isLoading: isLoadingFiles } = useQuery({
    queryKey: ['project-files', selectedProject?.id],
    queryFn: () => projectsApi.getProjectFiles(selectedProject!.id),
    enabled: !!selectedProject,
  });

  // Set default selection
  useEffect(() => {
    if (projects.length > 0 && !selectedProject) {
      setSelectedProject(projects[0]);
    }
  }, [projects, selectedProject]);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl">Projects & Files</h1>
          <p className="text-sm text-slate-400 mt-1">
            Projekt-Registry, File-Tree und Quick-Actions.
          </p>
        </div>
        <button className="flex items-center gap-2 px-3 py-2 bg-sheratan-accent/10 border border-sheratan-accent/40 text-sheratan-accent rounded-lg hover:bg-sheratan-accent/20 transition text-sm">
          <Plus className="w-4 h-4" />
          Register Project
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Project List */}
        <div className="lg:col-span-1 bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700">
            <h3 className="text-sm">Registered Projects</h3>
            <p className="text-xs text-slate-400 mt-0.5">{projects.length} total</p>
          </div>
          <div className="divide-y divide-slate-800">
            {isLoadingProjects ? (
              <div className="p-4 text-center text-xs text-slate-500 italic">Scanning Sheratan root...</div>
            ) : projects.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-500 italic">No projects found in C:\Sheratan</div>
            ) : projects.map((project) => (
              <button
                key={project.id}
                onClick={() => setSelectedProject(project)}
                className={`w-full text-left px-4 py-3 hover:bg-slate-900/40 transition ${selectedProject?.id === project.id ? "bg-sheratan-accent/5 border-l-2 border-sheratan-accent" : ""
                  }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <Folder className="w-4 h-4 text-sheratan-accent flex-shrink-0" />
                    <span className="text-sm text-slate-100">{project.name}</span>
                  </div>
                  <StatusPill
                    status={project.status}
                    variant={project.status === "active" ? "success" : "neutral"}
                  />
                </div>
                <p className="text-xs text-slate-400 line-clamp-1 ml-6">{project.path}</p>
                <div className="flex items-center gap-2 mt-1 ml-6 text-xs text-slate-500">
                  <span>{new Date(project.lastAccess).toLocaleDateString()}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* File Tree */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedProject ? (
            <div className="bg-sheratan-card border border-slate-700 rounded-lg p-12 text-center text-slate-500 italic">
              Select a project to view files.
            </div>
          ) : (
            <>
              <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
                <h3 className="text-sm mb-3">Project Info: {selectedProject.name}</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-xs text-slate-400">Path</span>
                    <div className="text-slate-200 mt-1 break-all">{selectedProject.path}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Status</span>
                    <div className="mt-1">
                      <StatusPill
                        status={selectedProject.status}
                        variant={selectedProject.status === "active" ? "success" : "neutral"}
                      />
                    </div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Project ID</span>
                    <div className="text-slate-200 mt-1">{selectedProject.id}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Last Access</span>
                    <div className="text-slate-200 mt-1">
                      {new Date(selectedProject.lastAccess).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm">File Tree</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {selectedProject.name} structure
                    </p>
                  </div>
                </div>
                <div className="p-2 max-h-[500px] overflow-y-auto">
                  {isLoadingFiles ? (
                    <div className="p-4 text-center text-xs text-slate-500 italic">Loading file tree...</div>
                  ) : fileTree.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-500 italic">No files found or access denied.</div>
                  ) : fileTree.map((node, i) => (
                    <FileTreeNode key={i} node={node} />
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
