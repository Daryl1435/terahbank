// Format dates for display — respects user locale (fr/en)

export const formatDate = (isoString: string, locale = 'fr'): string => {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat(locale === 'fr' ? 'fr-CM' : 'en-CM', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
};

export const formatDateTime = (isoString: string, locale = 'fr'): string => {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat(locale === 'fr' ? 'fr-CM' : 'en-CM', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

export const formatRelativeDate = (isoString: string, locale = 'fr'): string => {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return locale === 'fr' ? "Aujourd'hui" : 'Today';
  if (diffDays === 1) return locale === 'fr' ? 'Hier' : 'Yesterday';
  if (diffDays < 7) return formatDate(isoString, locale);

  return formatDate(isoString, locale);
};

export const daysUntil = (isoDateString: string): number => {
  const target = new Date(isoDateString);
  const now = new Date();
  const diffMs = target.getTime() - now.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
};
