'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useTranslation } from '@/lib/i18n';

interface PaginationProps {
  offset:       number;
  limit:        number;
  total:        number;
  onPageChange: (offset: number) => void;
}

export default function Pagination({ offset, limit, total, onPageChange }: PaginationProps) {
  const { t } = useTranslation();
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages  = Math.max(1, Math.ceil(total / limit));

  const rangeText = total === 0
    ? t('pagination.noResults')
    : t('pagination.range')
        .replace('{start}', String(offset + 1))
        .replace('{end}',   String(Math.min(offset + limit, total)))
        .replace('{total}', String(total));

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-light-grey text-sm text-mid-grey">
      <span>{rangeText}</span>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(offset - limit)}
          disabled={offset === 0}
          className="flex items-center gap-1 px-3 py-1 rounded border border-light-grey disabled:opacity-40 hover:bg-light-grey transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          {t('pagination.prev')}
        </button>
        <span className="px-3 py-1">
          {currentPage} / {totalPages}
        </span>
        <button
          onClick={() => onPageChange(offset + limit)}
          disabled={offset + limit >= total}
          className="flex items-center gap-1 px-3 py-1 rounded border border-light-grey disabled:opacity-40 hover:bg-light-grey transition-colors"
        >
          {t('pagination.next')}
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
