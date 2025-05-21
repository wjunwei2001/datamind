/**
 * DataMind API Service
 * Handles all API calls to the backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  metadata?: any;
}

export interface DatasetInfo {
  id: string;
  filename: string;
  description?: string;
  created_at: string;
  rows: number;
  columns: string[];
}

export interface DatasetMetadata {
  dataset_id: string;
  s3_key: string;
  filename: string;
  columns: string[];
  row_count: number;
  preview: any[];
  sample_data: string;
}

/**
 * Fetch and cache dataset metadata
 */
export async function getDatasetMetadata(datasetId: string): Promise<DatasetMetadata> {
  const response = await fetch(`${API_URL}/api/chat/dataset/${datasetId}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch dataset metadata: ${response.statusText}`);
  }
  
  return await response.json();
}

/**
 * Upload a file and get a session ID for analysis
 */
export async function uploadFile(file: File, context: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('description', context);
  
  const response = await fetch(`${API_URL}/api/datasets`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to upload file: ${response.statusText}`);
  }
  
  const data = await response.json();
  return {
    session_id: data.id,
    filename: data.filename,
    rows: data.rows,
    columns: data.columns
  };
}

/**
 * Send a message to the chat API
 */
export async function sendMessage(datasetId: string, message: string, cachedDataset?: DatasetMetadata) {
  // Create form data for the chat endpoint
  const formData = new FormData();
  formData.append('query', message);
  
  // Add cached dataset if available
  if (cachedDataset) {
    formData.append('cached_dataset', JSON.stringify(cachedDataset));
  }
  
  const response = await fetch(`${API_URL}/api/chat/stream/${datasetId}`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.statusText}`);
  }
  
  // Parse the event stream response
  // For simplicity, we'll just return the last complete result
  // In a real app, you'd process the event stream incrementally
  const reader = response.body?.getReader();
  let result = '';
  let finalResponse = null;
  let finalMessage = null;
  
  if (reader) {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      // Convert the Uint8Array to a string
      const chunk = new TextDecoder().decode(value);
      result += chunk;
      
      // Look for complete data entries (SSE format: "data: {...}\n\n")
      const dataEntries = result.split('\n\n');
      
      // Process all complete entries except the last one (which might be incomplete)
      for (let i = 0; i < dataEntries.length - 1; i++) {
        const entry = dataEntries[i].trim();
        if (entry.startsWith('data: ')) {
          try {
            const jsonData = JSON.parse(entry.substring(6)); // Remove "data: " prefix
            
            // Check for chat message format (for final story)
            if (jsonData.data && jsonData.data.chat_message) {
              finalMessage = jsonData.data.chat_message;
            }
            
            // Update our final response with the latest data
            if (jsonData.data && jsonData.data.analysis_results) {
              finalResponse = jsonData.data.analysis_results;
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }
      
      // Keep the last (potentially incomplete) entry for the next iteration
      result = dataEntries[dataEntries.length - 1];
    }
  }
  
  // Prefer the chat message format if available (for final story)
  if (finalMessage) {
    return {
      role: finalMessage.role as 'assistant' | 'user',
      content: finalMessage.content,
      metadata: finalMessage.metadata
    };
  }
  
  return {
    role: 'assistant' as const,
    content: finalResponse ? 
      finalResponse.answer || finalResponse.result || 'Analysis complete' : 
      'Sorry, I couldn\'t analyze your request.'
  };
}

/**
 * Get a list of all datasets
 */
export async function getDatasets(): Promise<DatasetInfo[]> {
  const response = await fetch(`${API_URL}/api/datasets`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch datasets');
  }
  
  return await response.json();
}

/**
 * For direct analysis without saving to the catalog
 */
export async function analyzeData(file: File, query: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('query', query);
  
  const response = await fetch(`${API_URL}/analyze`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error('Failed to analyze data');
  }
  
  // This is a streaming response, same processing as sendMessage
  const reader = response.body?.getReader();
  let result = '';
  let finalResponse = null;
  
  if (reader) {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      const chunk = new TextDecoder().decode(value);
      result += chunk;
      
      const dataEntries = result.split('\n\n');
      
      for (let i = 0; i < dataEntries.length - 1; i++) {
        const entry = dataEntries[i].trim();
        if (entry.startsWith('data: ')) {
          try {
            const jsonData = JSON.parse(entry.substring(6));
            
            if (jsonData.data && jsonData.data.analysis_results) {
              finalResponse = jsonData.data.analysis_results;
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }
      
      result = dataEntries[dataEntries.length - 1];
    }
  }
  
  return {
    response: finalResponse ? 
      finalResponse.answer || finalResponse.result || 'Analysis complete' : 
      'Sorry, I couldn\'t analyze your request.'
  };
}
  