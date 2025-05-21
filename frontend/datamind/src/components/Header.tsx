import Link from 'next/link';

export function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-10 bg-white/80 backdrop-blur-md border-b border-gray-100">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="text-purple-600 font-semibold text-2xl">
          DataMind
        </Link>
        <nav>
          <ul className="flex gap-6">
            <li>
              <Link href="/" className="text-gray-600 hover:text-purple-600 transition">
                Home
              </Link>
            </li>
            <li>
              <Link href="/chat" className="text-gray-600 hover:text-purple-600 transition">
                Chat
              </Link>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
} 