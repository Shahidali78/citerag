import type { Metadata } from 'next';
import './globals.css';
import AccessPanel from './components/AccessPanel';

export const metadata: Metadata = { title: 'CiteRAG — Evidence, not guesses', description: 'A grounded document assistant with verifiable source citations.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><AccessPanel/>{children}</body></html>;
}
