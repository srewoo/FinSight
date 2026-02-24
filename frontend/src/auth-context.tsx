import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, getToken, setToken, removeToken } from './api';

interface AuthContextType {
  user: { email: string } | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  getIdToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<{ email: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on mount
    const loadSession = async () => {
      try {
        const token = await getToken();
        if (token) {
          // Verify token by fetching profile
          const profile = await api.getUserProfile();
          setUser({ email: profile.email });
        }
      } catch (e) {
        // Token invalid or missing
        await removeToken();
      } finally {
        setLoading(false);
      }
    };
    loadSession();
  }, []);

  const value: AuthContextType = {
    user,
    loading,
    signIn: async (email, password) => {
      const data = new URLSearchParams();
      data.append('username', email);
      data.append('password', password);

      const res = await api.login(data);
      if (res.access_token) {
        await setToken(res.access_token);
        const profile = await api.getUserProfile();
        setUser({ email: profile.email });
      }
    },
    signUp: async (email, password) => {
      // In this version, signup happens via the admin provision endpoint or a new public register endpoint
      // We will just throw an error here to direct users to the admin flow for now wrapper
      throw new Error("Public registration disabled. Please contact admin.");
    },
    signOut: async () => {
      await removeToken();
      setUser(null);
    },
    resetPassword: async () => { },
    getIdToken: async () => getToken(),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
