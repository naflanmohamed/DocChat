export default function ChatPage({
  params,
}: {
  params: { sessionId: string };
}) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-3xl text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Chat</h1>
        <p className="text-gray-500 mb-4">Session: {params.sessionId}</p>
        <div className="border-2 border-dashed border-gray-300 rounded-xl p-16 text-gray-400">
          Chat UI — coming in Phase 6
        </div>
      </div>
    </main>
  );
}