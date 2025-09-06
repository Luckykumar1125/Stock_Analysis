import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';

interface Message {
  id: string;
  content: string;
  isBot: boolean;
  timestamp: Date;
}

export const Chatbot = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: "Hello! I'm your AI investment assistant powered by advanced machine learning. I can help you analyze stocks, explain market trends, assess risk profiles, and provide personalized recommendations. What would you like to explore today?",
      isBot: true,
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      isBot: false,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    
    // Simulate bot response
    setTimeout(() => {
      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: `Thank you for your question: "${inputValue}". I'm analyzing current market data and will provide you with insights based on the latest AI models and market trends.`,
        isBot: true,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, botResponse]);
    }, 1000);

    setInputValue('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  return (
    <Card className="glass-card border-card-border h-fit">
      <CardHeader>
        <CardTitle className="flex items-center">
          🤖 EquiLytix AI Assistant
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col h-80">
          <div className="flex-1 overflow-y-auto mb-4 space-y-3">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`p-3 rounded-lg max-w-[85%] animate-fade-in ${
                  message.isBot
                    ? 'bg-primary/10 border border-primary/20 mr-auto'
                    : 'bg-secondary/10 border border-secondary/20 ml-auto'
                }`}
              >
                <p className="text-sm leading-relaxed">{message.content}</p>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything about investments, market trends, or analysis..."
              className="flex-1 bg-background/50 border-card-border"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim()}
              className="gradient-primary shadow-primary hover:shadow-glow transition-all duration-300"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};