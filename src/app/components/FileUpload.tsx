import { Upload, X } from "lucide-react";
import { useState, useRef } from "react";
import { Button } from "./ui/button";

interface FileUploadProps {
  onFilesUploaded: (files: File[]) => void;
}

export function FileUpload({ onFilesUploaded }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      onFilesUploaded(files);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      onFilesUploaded(files);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      className={`
        border-2 border-dashed rounded-lg p-8
        transition-colors cursor-pointer
        ${isDragging 
          ? 'border-blue-500 bg-blue-50' 
          : 'border-gray-300 hover:border-gray-400 bg-gray-50'
        }
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileSelect}
        className="hidden"
      />
      <div className="flex flex-col items-center gap-2 text-center">
        <Upload className="size-10 text-gray-400" />
        <div>
          <p className="text-sm font-medium text-gray-700">
            Click to upload or drag and drop
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Support for multiple files
          </p>
        </div>
      </div>
    </div>
  );
}
