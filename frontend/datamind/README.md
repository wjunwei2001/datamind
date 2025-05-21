# DataMind Frontend

A modern React frontend for the DataMind data analysis platform.

## Features

- Upload and analyze CSV, Excel, and Parquet files up to 1GB
- Interactive chat interface for data analysis
- Visualize results with auto-generated charts
- Research integration with web intelligence
- Responsive design for all devices

## Setup Instructions

1. Install dependencies:

```bash
npm install
# or
yarn install
```

2. Create a `.env` file in the root directory with the following content:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Replace the URL with your backend API URL if it's different.

3. Run the development server:

```bash
npm run dev
# or
yarn dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser to see the application.

## Build for Production

```bash
npm run build
# or
yarn build
```

Then start the production server:

```bash
npm run start
# or
yarn start
```

## Architecture

The frontend is built with:

- **Next.js 15** - React framework with server-side rendering
- **TailwindCSS** - Utility-first CSS framework
- **React Hooks** - For state management and side effects
- **TypeScript** - For type safety and better developer experience

The application connects to the DataMind backend API which provides:

- File upload and analysis
- Chat interface with streaming responses
- Visualization generation
- Data storage and retrieval

## Folder Structure

- `src/app` - Next.js app router pages and layouts
- `src/lib` - Utility functions and API service
- `src/components` - Reusable UI components
- `public` - Static assets

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

## License

MIT
