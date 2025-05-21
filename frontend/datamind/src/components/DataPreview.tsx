import { useState } from 'react';
import { DatasetMetadata } from '@/lib/api';

interface DataPreviewProps {
  metadata: DatasetMetadata;
}

export function DataPreview({ metadata }: DataPreviewProps) {
  const [expanded, setExpanded] = useState(false);
  const [showAllColumns, setShowAllColumns] = useState(false);
  
  // Get column names from the preview data
  const columnNames = metadata?.columns || [];
  
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm mb-4 overflow-hidden">
      {/* Header with basic info and expand toggle */}
      <div 
        className="p-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div>
          <h3 className="font-medium text-gray-800 dark:text-gray-200">
            {metadata.filename}
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {metadata.row_count.toLocaleString()} rows • {columnNames.length} columns
          </p>
        </div>
        <button className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
          {expanded ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="18 15 12 9 6 15"></polyline>
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          )}
        </button>
      </div>
      
      {/* Expandable data preview table */}
      {expanded && (
        <div className="p-4">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Data Preview</h4>
          
          <div className="overflow-x-auto max-h-96 shadow-inner border border-gray-200 dark:border-gray-700 rounded-lg">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm" style={{ tableLayout: 'fixed' }}>
              <thead className="bg-gray-50 dark:bg-gray-900 sticky top-0 z-10">
                <tr>
                  {columnNames.map((column, index) => (
                    <th 
                      key={index} 
                      className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 truncate"
                      style={{ minWidth: '150px', maxWidth: '250px' }}
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {metadata.preview.map((row, rowIndex) => (
                  <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-900'}>
                    {columnNames.map((column, colIndex) => (
                      <td 
                        key={colIndex} 
                        className="px-3 py-2 whitespace-nowrap text-gray-700 dark:text-gray-300 truncate"
                        style={{ minWidth: '150px', maxWidth: '250px' }}
                        title={row[column] !== null ? String(row[column]) : 'N/A'}
                      >
                        {row[column] !== null ? String(row[column]).substring(0, 50) : 'N/A'}
                        {row[column] !== null && String(row[column]).length > 50 ? '...' : ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="mt-4 flex justify-between text-xs text-gray-500 dark:text-gray-400">
            <p>Showing {metadata.preview.length} of {metadata.row_count.toLocaleString()} rows</p>
          </div>
        </div>
      )}
      
      {/* Column overview */}
      {expanded && (
        <div className="p-4 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Column Overview</h4>
          <div className="overflow-x-auto pb-2">
            <div className="flex flex-nowrap gap-2" style={{ minWidth: 'min-content' }}>
              {(showAllColumns ? columnNames : columnNames.slice(0, 12)).map((column, index) => (
                <div key={index} className="bg-white dark:bg-gray-800 p-1.5 rounded border border-gray-200 dark:border-gray-700 text-xs" style={{ minWidth: '150px' }}>
                  <div className="font-medium text-gray-800 dark:text-gray-200 truncate" title={column}>
                    {column}
                  </div>
                  <div className="text-gray-500 dark:text-gray-400 mt-0.5">
                    {getColumnType(metadata.preview, column)}
                  </div>
                </div>
              ))}
              {!showAllColumns && columnNames.length > 12 && (
                <div 
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowAllColumns(true);
                  }}
                  className="bg-white dark:bg-gray-800 p-1.5 rounded border border-gray-200 dark:border-gray-700 text-xs flex items-center justify-center text-gray-500 dark:text-gray-400 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
                  style={{ minWidth: '120px' }}
                >
                  + {columnNames.length - 12} more columns
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper function to guess column type based on data
function getColumnType(data: any[], columnName: string): string {
  if (!data || data.length === 0) return 'Unknown';
  
  // Get non-null values
  const values = data
    .map(row => row[columnName])
    .filter(val => val !== null && val !== undefined);
  
  if (values.length === 0) return 'Empty';
  
  // Check first non-null value
  const sample = values[0];
  
  if (typeof sample === 'number') return 'Numeric';
  if (typeof sample === 'boolean') return 'Boolean';
  
  // Check if it's a date
  if (typeof sample === 'string') {
    if (sample.match(/^\d{4}-\d{2}-\d{2}/) || sample.match(/^\d{2}\/\d{2}\/\d{4}/)) {
      return 'Date';
    }
    if (sample.length > 50) return 'Text (Long)';
    return 'Text';
  }
  
  return 'Mixed';
} 