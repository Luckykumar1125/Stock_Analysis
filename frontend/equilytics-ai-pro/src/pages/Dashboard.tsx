import { useState } from 'react';
import { Navigation } from '@/components/Navigation';
import { Hero } from '@/components/Hero';
import { ChartContainer } from '@/components/ChartContainer';
import { AIInsights } from '@/components/AIInsights';
import { Chatbot } from '@/components/Chatbot';
import { Watchlist } from '@/components/Watchlist';
import { NewsSection } from '@/components/NewsSection';
import { ToolsGrid } from '@/components/ToolsGrid';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="min-h-screen bg-background">
      <Navigation activeTab={activeTab} onTabChange={setActiveTab} />
      
      <main className="container mx-auto">
        {/* Dashboard Section */}
        <section id="dashboard">
          <Hero />
        </section>
        
        <div className="px-6 pb-8">
          {/* Analytics Section */}
          <section id="analytics" className="pt-16">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
              <div className="lg:col-span-2 space-y-8">
                <ChartContainer />
                <AIInsights />
              </div>
              
              <div className="space-y-8">
                <Chatbot />
                <Watchlist />
              </div>
            </div>
          </section>
          
          {/* Insights Section */}
          <section id="insights" className="pt-16">
            <NewsSection />
          </section>
          
          {/* Tools Section */}
          <section id="tools" className="pt-16">
            <ToolsGrid />
          </section>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
