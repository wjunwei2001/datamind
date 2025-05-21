import { useState } from 'react';

interface DataContextProps {
  onSubmit: (context: string) => void;
}

export function DataContext({ onSubmit }: DataContextProps) {
  const [context, setContext] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (context.trim()) {
      onSubmit(context);
    }
  };
  
  return (
    <div className="w-full">
      <h3 className="text-lg font-medium mb-2">Data Context</h3>
      <form onSubmit={handleSubmit}>
        <textarea
          className="w-full p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent min-h-[120px] resize-none"
          placeholder="Provide information about your dataset (e.g., 'Customer purchase history from Q1 2023' or 'Product inventory with seasonal variations')"
          value={context}
          onChange={(e) => setContext(e.target.value)}
        />
        <div className="flex justify-end mt-3">
          <button 
            type="submit"
            className={`px-6 py-2 rounded-full font-medium ${
              !context.trim() 
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                : 'bg-purple-600 text-white hover:bg-purple-700'
            }`}
            disabled={!context.trim()}
          >
            Analyze
          </button>
        </div>
      </form>
    </div>
  );
} 