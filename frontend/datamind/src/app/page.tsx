'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/Header';
import { FileUpload } from '@/components/FileUpload';
import { DataContext } from '@/components/DataContext';
import { uploadFile } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    setError(null);
  };
  
  const handleContextSubmit = async (context: string) => {
    if (!file) {
      setError('Please upload a file first');
      return;
    }
    
    try {
      setIsUploading(true);
      setError(null);
      
      const result = await uploadFile(file, context);
      console.log('Upload result:', result);
      
      // Navigate to chat page with the dataset ID
      router.push(`/chat?session=${result.session_id}`);
    } catch (err: any) {
      console.error('Upload error:', err);
      setError(`Failed to upload file: ${err.message || 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-500 to-pink-500">
      <Header />
      
      <main className="pt-24 px-4 container mx-auto flex flex-col items-center">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-4">
            Chat with your data
          </h1>
          <p className="text-xl text-white/80 max-w-2xl mx-auto">
            Upload your dataset and ask questions to get insights
          </p>
        </div>
        
        <div className="bg-white rounded-2xl shadow-lg p-6 md:p-8 w-full max-w-3xl">
          {!file ? (
            <FileUpload onFileSelect={handleFileSelect} />
          ) : (
            <div className="space-y-6">
              <div className="flex items-center justify-between bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 bg-purple-100 rounded-full flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium truncate">{file.name}</p>
                    <p className="text-sm text-gray-500">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                  </div>
                </div>
                <button 
                  onClick={() => setFile(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <DataContext onSubmit={handleContextSubmit} />
              
              {error && (
                <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
                  {error}
                </div>
              )}
              
              {isUploading && (
                <div className="flex justify-center">
                  <div className="flex items-center gap-2 text-purple-600">
                    <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Uploading and processing your data...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        
        <div className="mt-6 text-center text-white/70 text-sm">
          Your data is processed securely and never shared with third parties
        </div>
      </main>
    </div>
  );
}
