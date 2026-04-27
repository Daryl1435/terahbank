'use client';

interface PaginationProps {
  offset: number;
  limit: number;
  total: number;
  onPageChange: (offset: number) => void;
}

export default function Pagination({ offset, limit, total, onPageChange }: PaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages  = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-light-grey text-sm text-mid-grey">
      <span>
        {total === 0
          ? 'Aucun résultat'
          : `${offset + 1}–${Math.min(offset + limit, total)} sur ${total}`}
      </span>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(offset - limit)}
          disabled={offset === 0}
          className="px-3 py-1 rounded border border-light-grey disabled:opacity-40 hover:bg-light-grey transition-colors"
        >
          ← Préc.
        </button>
        <span className="px-3 py-1">
          {currentPage} / {totalPages}
        </span>
        <button
          onClick={() => onPageChange(offset + limit)}
          disabled={offset + limit >= total}
          className="px-3 py-1 rounded border border-light-grey disabled:opacity-40 hover:bg-light-grey transition-colors"
        >
          Suiv. →
        </button>
      </div>
    </div>
  );
}
