export default function LoadingSpinner({ className = '' }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="Chargement…"
      className={`inline-block w-5 h-5 border-2 border-teal border-t-transparent rounded-full animate-spin ${className}`}
    />
  );
}
