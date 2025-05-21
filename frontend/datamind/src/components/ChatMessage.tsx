import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessageProps {
  message: {
    role: 'user' | 'assistant';
    content: string;
    metadata?: any;
  };
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isMarkdown = message.role === 'assistant' && 
    (message.content.includes('#') || 
     message.content.includes('*') || 
     message.content.includes('```') ||
     message.content.includes('-'));
  
  // Custom styling for markdown elements
  const markdownStyles = {
    // Add custom styles for code blocks
    code: ({ node, inline, className, children, ...props }: any) => {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <div className="bg-gray-800 rounded-md p-2 my-2 overflow-x-auto">
          <code className={`${className} text-sm text-gray-100`} {...props}>
            {children}
          </code>
        </div>
      ) : (
        <code className="bg-gray-200 px-1 py-0.5 rounded text-sm" {...props}>
          {children}
        </code>
      );
    },
    // Style for headings
    h1: ({ children }: any) => <h1 className="text-xl font-bold mt-6 mb-2">{children}</h1>,
    h2: ({ children }: any) => <h2 className="text-lg font-bold mt-5 mb-2">{children}</h2>,
    h3: ({ children }: any) => <h3 className="text-md font-bold mt-4 mb-2">{children}</h3>,
  };

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div 
        className={`rounded-lg p-4 max-w-[80%] ${
          isUser 
            ? 'bg-purple-600 text-white rounded-tr-none' 
            : 'bg-gray-100 text-gray-800 rounded-tl-none'
        }`}
        style={{ width: isMarkdown ? '95%' : 'auto' }}
      >
        {isMarkdown ? (
          <div className="prose prose-slate dark:prose-invert prose-headings:my-3 prose-p:my-2 prose-ul:my-2 prose-li:my-0 max-w-none">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]} 
              components={markdownStyles}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}
      </div>
    </div>
  );
} 