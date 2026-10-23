import { getRequestConfig } from 'next-intl/server';
import { routing } from './routing';

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = (routing.locales as readonly string[]).includes(requested ?? '')
    ? (requested as 'en' | 'bn')
    : (routing.defaultLocale as 'en' | 'bn');
  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
