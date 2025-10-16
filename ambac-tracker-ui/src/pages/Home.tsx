export default function Home() {
    return (
        <div className="min-h-full">
            {/* Hero Section */}
            <section className="px-6 py-16">
                <div className="max-w-4xl mx-auto text-center">
                    <h1 className="text-4xl md:text-5xl font-bold mb-6">
                        AMBAC Quality Tracker
                    </h1>
                    <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
                        Track your orders, view quality reports, and monitor production progress
                        with our comprehensive manufacturing management system.
                    </p>
                </div>
            </section>
        </div>
    );
}