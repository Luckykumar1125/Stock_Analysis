export const Hero = () => {
  return (
    <section className="relative py-16 px-6 text-center overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-secondary/5 to-transparent" />
      <div className="relative z-10 max-w-4xl mx-auto">
        <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
          <span className="gradient-primary bg-clip-text text-transparent">
            Advanced Equity Analytics
          </span>
        </h1>
        <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
          Harness the power of AI-driven market analysis with real-time data insights, 
          predictive analytics, and personalized investment recommendations powered by 
          cutting-edge machine learning.
        </p>
      </div>
    </section>
  );
};