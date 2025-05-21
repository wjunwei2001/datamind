'use client';

import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { Header } from '@/components/Header';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInput } from '@/components/ChatInput';
import { DataPreview } from '@/components/DataPreview';
import { sendMessage, Message, getDatasetMetadata, DatasetMetadata } from '@/lib/api';

export default function ChatPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hi! I\'ve analyzed your dataset. Ask me anything about it!',
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [datasetMetadata, setDatasetMetadata] = useState<DatasetMetadata | null>(null);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState(false);
  const [showDataPreview, setShowDataPreview] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Fetch dataset metadata on page load
  useEffect(() => {
    if (sessionId) {
      const fetchMetadata = async () => {
        try {
          setIsLoadingMetadata(true);
          const metadata = await getDatasetMetadata(sessionId);
          setDatasetMetadata(metadata);
          
          // Update initial message with dataset info
          setMessages([{
            role: 'assistant',
            content: `Hi! I've loaded your dataset "${metadata.filename}" with ${metadata.row_count.toLocaleString()} rows and ${metadata.columns.length} columns. What would you like to know about it?`,
          }]);
        } catch (err: any) {
          console.error('Failed to fetch dataset metadata:', err);
          setError(`Failed to load dataset information: ${err.message}`);
        } finally {
          setIsLoadingMetadata(false);
        }
      };
      
      fetchMetadata();
    }
  }, [sessionId]);
  
  const handleSendMessage = async (content: string) => {
    if (!sessionId) {
      setError('No dataset found. Please upload a dataset first.');
      return;
    }
    
    // Add user message to the chat
    const userMessage: Message = { role: 'user', content };
    setMessages((prev) => [...prev, userMessage]);
    
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('Sending message to dataset:', sessionId);
      // Pass cached dataset metadata if available
      const response = await sendMessage(sessionId, content);
      console.log('Message response:', response);
      
      // Add assistant message to the chat
      setMessages((prev) => [...prev, {
        role: response.role as 'assistant' | 'user',
        content: response.content || 'Sorry, I couldn\'t process that request.',
        metadata: response.metadata
      }]);
    } catch (err: any) {
      console.error('Message error:', err);
      setError(`Failed to send message: ${err.message || 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };
  
  if (!sessionId) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="pt-24 px-4 container mx-auto">
          <div className="max-w-3xl mx-auto bg-white p-8 rounded-2xl shadow-sm">
            <h1 className="text-2xl font-semibold text-center mb-4">No Dataset Found</h1>
            <p className="text-gray-600 text-center">
              Please upload a dataset on the home page first.
            </p>
          </div>
        </main>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="pt-24 pb-8 px-4 container mx-auto flex flex-col h-[calc(100vh-64px)]">
        <div className="max-w-3xl w-full mx-auto flex flex-col flex-grow overflow-hidden">
          {/* Dataset Info & Preview */}
          <div className="mb-4">
            {isLoadingMetadata ? (
              <div className="bg-white p-4 rounded-lg shadow-sm mb-4">
                <div className="flex items-center space-x-2">
                  <div className="animate-spin h-4 w-4 border-t-2 border-purple-600 border-r-2 border-transparent rounded-full"></div>
                  <p className="text-sm text-gray-500">Loading dataset information...</p>
                </div>
              </div>
            ) : datasetMetadata ? (
              <>
                <DataPreview metadata={datasetMetadata} />
              </>
            ) : (
              <div className="bg-white p-4 rounded-lg shadow-sm mb-4">
                <p className="text-sm text-gray-500">Dataset ID: {sessionId}</p>
              </div>
            )}
          </div>
          
          {/* Chat Interface */}
          <div className="bg-white rounded-2xl shadow-sm flex flex-col flex-grow overflow-hidden">
            <div className="p-4 border-b border-gray-100">
              <h1 className="text-xl font-semibold">Chat with your data</h1>
              {datasetMetadata && (
                <p className="text-sm text-gray-500">
                  Analyzing {datasetMetadata.filename}
                </p>
              )}
            </div>
            
            <div className="flex-grow overflow-y-auto p-4 space-y-6">
              {messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))}
              
              {isLoading && (
                <div className="flex justify-center py-4">
                  <div className="flex items-center gap-2 text-purple-600">
                    <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Thinking...</span>
                  </div>
                </div>
              )}
              
              {error && (
                <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
                  {error}
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
            
            <div className="p-4 border-t border-gray-100">
              <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 