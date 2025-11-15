import React, { useState, useEffect, useRef, ElementRef } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
      content: "Hello! I'm your AI investment assistant. I can help you analyze stocks, explain market trends, assess risk profiles, and more. What's on your mind?",
      isBot: true,
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<ElementRef<"div">>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      isBot: false,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const response = await axios.post('http://127.0.0.1:8000/chat', {
        query: inputValue,
      });

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.data.answer || "Sorry, I couldn't get a response.",
        isBot: true,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const botMessage: Message = {
        id: (Date.now() + 2).toString(),
        content: "Oops! Something went wrong while contacting the server.",
        isBot: true,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, botMessage]);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      handleSendMessage();
    }
  };

  return (
    <Card className="glass-card border-card-border h-fit">
      <CardHeader>
        <CardTitle className="flex items-center">
          EquiLytix AI Assistant
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col h-[700px]">
          {/* Chat message feed */}
          <div className="flex-1 overflow-y-auto mb-4 space-y-4 p-2 scroll-smooth">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`p-3 rounded-lg max-w-[85%] animate-fade-in ${
                  message.isBot
                    ? 'bg-muted text-muted-foreground mr-auto' // Bot: High contrast background
                    : 'bg-primary text-primary-foreground ml-auto' // User: Brand color
                }`}
              >
                {message.isBot ? (
                  <Markdown
                    remarkPlugins={[remarkGfm]}
                    // Add styling for markdown elements
                    components={{
                      p: ({ node, ...props }) => <p className="leading-relaxed" {...props} />,
                      ul: ({ node, ...props }) => <ul className="list-disc list-inside my-2" {...props} />,
                      ol: ({ node, ...props }) => <ol className="list-decimal list-inside my-2" {...props} />,
                      li: ({ node, ...props }) => <li className="my-1" {...props} />,
                      
                      // === THIS IS THE FIX ===
                      // We explicitly add types to the function's parameters
                      code: ({ node, inline, ...props }: { node: any; inline?: boolean; [key: string]: any }) => 
                        inline ? (
                          // Inline code
                          <code className="bg-primary/10 text-primary px-1 py-0.5 rounded" {...props} />
                        ) : (
                          // Code block
                          <code className="block w-full overflow-auto bg-black/10 dark:bg-white/10 p-2 rounded" {...props} />
                        ),
                      // === END OF FIX ===
                        
                      a: ({ node, ...props }) => <a className="text-primary hover:underline" {...props} />,
                    }}
                  >
                    {message.content}
                  </Markdown>
                ) : (
                  // User's message is just plain text
                  <p className="text-sm leading-relaxed">{message.content}</p>
                )}
              </div>
            ))}
            
            {/* Loading bubble */}
            {loading && (
              <div className="p-3 rounded-lg max-w-[85%] bg-muted text-muted-foreground mr-auto animate-pulse">
                <p className="text-sm leading-relaxed">Thinking...</p>
              </div>
            )}
            
            {/* Self-scrolling anchor */}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Input bar */}
          <div className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything..."
              className="flex-1 bg-background/50 border-card-border"
              disabled={loading}
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || loading}
              className="gradient-primary shadow-primary hover:shadow-glow transition-all duration-300"
            >
              {loading ? (
                // Simple loading spinner for the button
                <div className="h-4 w-4 border-2 border-t-transparent border-white rounded-full animate-spin"></div>
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};