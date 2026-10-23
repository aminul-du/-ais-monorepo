import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'MCore',
  description: 'Engineering Intelligence for the World. Meticulous Core Ltd.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><body>{children}</body></html>);
}
