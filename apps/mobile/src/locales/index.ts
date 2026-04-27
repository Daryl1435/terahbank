import { I18n } from 'i18n-js';
import * as Localization from 'expo-localization';
import fr from './fr.json';
import en from './en.json';

const i18n = new I18n({ fr, en });
i18n.locale = Localization.getLocales()[0]?.languageCode ?? 'fr';
i18n.enableFallback = true;
i18n.defaultLocale = 'fr';

export default i18n;

// Usage: import i18n from '@/locales';
//        <Text>{i18n.t('dashboard.total_balance')}</Text>
//        <Text>{i18n.t('dashboard.greeting_morning', { name: user.full_name })}</Text>
