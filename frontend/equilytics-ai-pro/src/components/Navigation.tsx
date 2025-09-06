import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface NavigationProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const Navigation = ({ activeTab, onTabChange }: NavigationProps) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'analytics', label: 'Analytics' },
    { id: 'portfolio', label: 'Portfolio' },
    { id: 'tools', label: 'Tools' },
    { id: 'insights', label: 'Insights' },
  ];

  return (
    <nav className="glass-card border-b border-card-border">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <div className="text-2xl font-bold gradient-primary bg-clip-text text-transparent">
              EquiLytix
            </div>
            <div className="hidden md:flex space-x-6">
              {navItems.map((item) => (
                <Button
                  key={item.id}
                  variant={activeTab === item.id ? "default" : "ghost"}
                  onClick={() => onTabChange(item.id)}
                  className={`transition-all duration-300 ${
                    activeTab === item.id 
                      ? 'gradient-primary shadow-primary hover:shadow-primary' 
                      : 'hover:bg-accent/50'
                  }`}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};