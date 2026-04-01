import { useState } from "react";
import { File, Folder, MoreVertical, Trash2, FolderPlus, X } from "lucide-react";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  uploadDate: Date;
  groupId: string | null;
  meetingId?: number | null;
}

export interface FileGroup {
  id: string;
  name: string;
  color: string;
}

interface FileManagerProps {
  files: UploadedFile[];
  groups: FileGroup[];
  onDeleteFile: (fileId: string) => void;
  onMoveToGroup: (fileId: string, groupId: string | null) => void;
  onCreateGroup: (name: string) => void;
  onDeleteGroup: (groupId: string) => void;
}

export function FileManager({
  files,
  groups,
  onDeleteFile,
  onMoveToGroup,
  onCreateGroup,
  onDeleteGroup,
}: FileManagerProps) {
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [isCreatingGroup, setIsCreatingGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const handleCreateGroup = () => {
    if (newGroupName.trim()) {
      onCreateGroup(newGroupName.trim());
      setNewGroupName("");
      setIsCreatingGroup(false);
    }
  };

  const filteredFiles = selectedGroup === null
    ? files.filter(f => f.groupId === null)
    : selectedGroup === "all"
    ? files
    : files.filter(f => f.groupId === selectedGroup);

  const ungroupedCount = files.filter(f => f.groupId === null).length;

  return (
    <div className="flex flex-col h-full">
      {/* Groups Section */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm">Groups</h3>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsCreatingGroup(true)}
          >
            <FolderPlus className="size-4" />
          </Button>
        </div>

        {isCreatingGroup && (
          <div className="flex gap-2 mb-2">
            <Input
              placeholder="Group name"
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateGroup();
                if (e.key === 'Escape') {
                  setIsCreatingGroup(false);
                  setNewGroupName("");
                }
              }}
              autoFocus
              className="h-8 text-sm"
            />
            <Button size="sm" onClick={handleCreateGroup} className="h-8">
              Add
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setIsCreatingGroup(false);
                setNewGroupName("");
              }}
              className="h-8"
            >
              <X className="size-4" />
            </Button>
          </div>
        )}

        <div className="space-y-1">
          <button
            onClick={() => setSelectedGroup("all")}
            className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
              selectedGroup === "all"
                ? "bg-blue-50 text-blue-700"
                : "hover:bg-gray-100 text-gray-700"
            }`}
          >
            <Folder className="size-4" />
            <span>All Files</span>
            <Badge variant="secondary" className="ml-auto text-xs">
              {files.length}
            </Badge>
          </button>

          <button
            onClick={() => setSelectedGroup(null)}
            className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
              selectedGroup === null
                ? "bg-blue-50 text-blue-700"
                : "hover:bg-gray-100 text-gray-700"
            }`}
          >
            <Folder className="size-4" />
            <span>Ungrouped</span>
            <Badge variant="secondary" className="ml-auto text-xs">
              {ungroupedCount}
            </Badge>
          </button>

          {groups.map((group) => {
            const count = files.filter(f => f.groupId === group.id).length;
            return (
              <div
                key={group.id}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                  selectedGroup === group.id
                    ? "bg-blue-50 text-blue-700"
                    : "hover:bg-gray-100 text-gray-700"
                }`}
              >
                <button
                  onClick={() => setSelectedGroup(group.id)}
                  className="flex items-center gap-2 flex-1 text-left"
                >
                  <div
                    className="size-3 rounded-full"
                    style={{ backgroundColor: group.color }}
                  />
                  <span>{group.name}</span>
                  <Badge variant="secondary" className="ml-auto text-xs">
                    {count}
                  </Badge>
                </button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onDeleteGroup(group.id)}
                  className="h-6 w-6 p-0 opacity-0 hover:opacity-100"
                >
                  <Trash2 className="size-3" />
                </Button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Files List */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="font-semibold text-sm mb-3">
          {selectedGroup === "all"
            ? "All Files"
            : selectedGroup === null
            ? "Ungrouped Files"
            : groups.find(g => g.id === selectedGroup)?.name || "Files"}
        </h3>

        {filteredFiles.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm">
            No files {selectedGroup !== "all" && "in this group"}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-3 p-3 rounded-lg border bg-white hover:bg-gray-50 transition-colors"
              >
                <File className="size-8 text-gray-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(file.size)} • {file.uploadDate.toLocaleDateString()}
                  </p>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                      <MoreVertical className="size-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => onMoveToGroup(file.id, null)}
                    >
                      Move to Ungrouped
                    </DropdownMenuItem>
                    {groups.map((group) => (
                      <DropdownMenuItem
                        key={group.id}
                        onClick={() => onMoveToGroup(file.id, group.id)}
                      >
                        <div className="flex items-center gap-2">
                          <div
                            className="size-2 rounded-full"
                            style={{ backgroundColor: group.color }}
                          />
                          Move to {group.name}
                        </div>
                      </DropdownMenuItem>
                    ))}
                    <DropdownMenuItem
                      onClick={() => onDeleteFile(file.id)}
                      className="text-red-600"
                    >
                      <Trash2 className="size-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
