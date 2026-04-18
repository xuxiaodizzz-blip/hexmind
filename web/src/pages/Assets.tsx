import { useState, useRef, useCallback } from 'react';
import { motion } from 'motion/react';
import { Upload, FileText, Image, Trash2, X, File } from 'lucide-react';
import { cn } from '../lib/utils';
import { ACCEPTED_EXTENSIONS, ACCEPTED_MIME_TYPES, MAX_FILE_SIZE_MB } from '../data/personas';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { useLanguage } from '../hooks/useLanguage';

interface AssetFile {
  id: string;
  name: string;
  size: number;
  type: string;
  addedAt: string;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(type: string) {
  if (type.startsWith('image/')) return Image;
  if (type === 'application/pdf' || type.includes('document')) return FileText;
  return File;
}

export default function Assets() {
  const { t } = useLanguage();
  const [files, setFiles] = useLocalStorage<AssetFile[]>('hexmind-assets', []);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback(
    (fileList: FileList) => {
      const newFiles: AssetFile[] = [];
      for (const f of Array.from(fileList)) {
        const ext = '.' + f.name.split('.').pop()?.toLowerCase();
        if (!ACCEPTED_EXTENSIONS.includes(ext)) continue;
        if (f.size > MAX_FILE_SIZE_MB * 1024 * 1024) continue;
        newFiles.push({
          id: crypto.randomUUID(),
          name: f.name,
          size: f.size,
          type: f.type || 'application/octet-stream',
          addedAt: new Date().toISOString(),
        });
      }
      if (newFiles.length) setFiles((prev) => [...prev, ...newFiles]);
    },
    [setFiles],
  );

  const removeFile = (id: string) => setFiles((prev) => prev.filter((f) => f.id !== id));

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full bg-[#0b0f17] text-white">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <h1 className="text-4xl font-bold font-sans mb-2 tracking-tight">{t('assets.title')}</h1>
          <p className="text-white/50 font-serif italic text-lg">
            {t('assets.subtitle')}
          </p>
        </motion.div>

        {/* Upload Zone */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={cn(
            'border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors mb-10',
            dragOver
              ? 'border-[#00e5ff] bg-[#00e5ff]/5'
              : 'border-white/10 hover:border-white/20 bg-[#151a23]',
          )}
        >
          <Upload className={cn('w-10 h-10 mx-auto mb-4', dragOver ? 'text-[#00e5ff]' : 'text-white/30')} />
          <p className="text-white/70 font-sans font-medium mb-2">{t('assets.dragHint')}</p>
          <p className="text-white/40 text-sm">
            {t('assets.supportedFormats', { formats: ACCEPTED_EXTENSIONS.join(', '), size: String(MAX_FILE_SIZE_MB) })}
          </p>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED_MIME_TYPES}
            className="hidden"
            onChange={(e) => e.target.files && addFiles(e.target.files)}
          />
        </motion.div>

        {/* File List */}
        {files.length === 0 ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-16 text-white/30">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p className="font-serif italic text-lg">{t('assets.noFiles')}</p>
          </motion.div>
        ) : (
          <div className="space-y-3">
            <div className="flex justify-between items-center mb-4">
              <p className="text-sm text-white/50">{t('assets.fileCount', { count: String(files.length) })}</p>
              <button
                onClick={() => setFiles([])}
                className="text-xs text-white/40 hover:text-red-400 transition-colors flex items-center gap-1"
              >
                <X className="w-3 h-3" /> {t('assets.clearAll')}
              </button>
            </div>
            {files.map((file, i) => {
              const Icon = getFileIcon(file.type);
              return (
                <motion.div
                  key={file.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-center gap-4 p-4 bg-[#151a23] border border-white/5 rounded-xl hover:border-white/10 transition-colors"
                >
                  <div className="w-10 h-10 rounded-lg bg-[#1e2430] flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-white/50" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{file.name}</p>
                    <p className="text-xs text-white/40">{formatSize(file.size)}</p>
                  </div>
                  <button
                    onClick={() => removeFile(file.id)}
                    className="p-2 text-white/30 hover:text-red-400 transition-colors shrink-0"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
