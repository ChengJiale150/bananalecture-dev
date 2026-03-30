'use client';

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

interface BasePathContextValue {
  basePath: string;
  isLoading: boolean;
}

const BasePathContext = createContext<BasePathContextValue>({
  basePath: '',
  isLoading: true,
});

export function BasePathProvider({ children }: { children: ReactNode }) {
  const [basePath, setBasePath] = useState('');

  useEffect(() => {
    const loadBasePath = async () => {
      try {
        const response = await fetch('/api/config');
        const data = await response.json();
        setBasePath(data.basePath || '');
      } catch (error) {
        console.error('Failed to load base path:', error);
        setBasePath('');
      }
    };
    void loadBasePath();
  }, []);

  return (
    <BasePathContext.Provider value={{ basePath, isLoading: false }}>
      {children}
    </BasePathContext.Provider>
  );
}

export function useBasePath() {
  return useContext(BasePathContext);
}
