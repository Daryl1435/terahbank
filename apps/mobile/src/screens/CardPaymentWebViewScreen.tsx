/**
 * FR-038: Hosted card payment WebView (PCI-DSS SAQ-A).
 *
 * Opens the partner's PCI-certified hosted payment page in an embedded WebView.
 * User enters card details on the partner's page — raw PAN never touches TerahBank.
 *
 * Flow:
 *   1. POST /transactions/deposit (channel=visa) → payment_url returned (202).
 *   2. This screen opens payment_url in WebView.
 *   3. Partner redirects to success_url or cancel_url on completion.
 *   4. We detect the redirect and navigate accordingly.
 *   5. Webhook arrives separately → CardService credits account.
 *
 * The success/cancel URLs come from VISA_GATEWAY_SUCCESS_URL / VISA_GATEWAY_CANCEL_URL
 * configured in the backend (https://app.terahbank.com/deposit/success?ref=TXN-...).
 */
import React, { useRef, useState } from 'react';
import {
  View,
  Text,
  ActivityIndicator,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { WebView, WebViewNavigation } from 'react-native-webview';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../../App';
import { colors, spacing } from '@/utils/tokens';
import i18n from '@/locales';

type CardPaymentNavProp  = NativeStackNavigationProp<RootStackParamList, 'CardPaymentWebView'>;
type CardPaymentRouteProp = RouteProp<RootStackParamList, 'CardPaymentWebView'>;

interface CardPaymentWebViewScreenProps {
  navigation: CardPaymentNavProp;
  route: CardPaymentRouteProp;
}

// Detect redirect to our success / cancel URLs
const SUCCESS_HOST = 'app.terahbank.com';
const CANCEL_HOST  = 'app.terahbank.com';
const SUCCESS_PATH = '/deposit/success';
const CANCEL_PATH  = '/deposit/cancel';

function isSuccessUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.hostname === SUCCESS_HOST && parsed.pathname === SUCCESS_PATH;
  } catch {
    return url.includes(SUCCESS_PATH);
  }
}

function isCancelUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.hostname === CANCEL_HOST && parsed.pathname === CANCEL_PATH;
  } catch {
    return url.includes(CANCEL_PATH);
  }
}

export default function CardPaymentWebViewScreen({ navigation, route }: CardPaymentWebViewScreenProps) {
  const { paymentUrl, transactionId, reference } = route.params;
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(false);
  const handled = useRef(false);   // Guard against double navigation

  const handleNavigationStateChange = (navState: WebViewNavigation) => {
    const url = navState.url;
    if (handled.current) return;

    if (isSuccessUrl(url)) {
      handled.current = true;
      // Payment submitted — navigate to status screen to poll for webhook confirmation
      navigation.replace('TransactionDetail', { transactionId, reference });
      return;
    }

    if (isCancelUrl(url)) {
      handled.current = true;
      navigation.goBack();
    }
  };

  const handleCancel = () => {
    Alert.alert(
      i18n.t('card_payment.cancel_title'),
      i18n.t('card_payment.cancel_message'),
      [
        { text: i18n.t('common.continue'), style: 'cancel' },
        {
          text: i18n.t('common.exit'),
          style: 'destructive',
          onPress: () => navigation.goBack(),
        },
      ],
    );
  };

  if (!paymentUrl) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.errorText}>{i18n.t('card_payment.no_url')}</Text>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backBtnText}>{i18n.t('common.back')}</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      {/* Minimal header with cancel */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.headerTitle}>{i18n.t('card_payment.title')}</Text>
          <Text style={styles.headerSub}>{i18n.t('card_payment.secure_hint')}</Text>
        </View>
        <TouchableOpacity
          onPress={handleCancel}
          style={styles.cancelBtn}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('common.cancel')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={styles.cancelText}>{i18n.t('common.cancel')}</Text>
        </TouchableOpacity>
      </View>

      {/* Loading indicator overlaid on WebView */}
      {loading && !error && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color={colors.teal} />
          <Text style={styles.loadingText}>{i18n.t('card_payment.loading')}</Text>
        </View>
      )}

      {error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{i18n.t('card_payment.load_error')}</Text>
          <TouchableOpacity onPress={() => { setError(false); setLoading(true); }} style={styles.backBtn}>
            <Text style={styles.backBtnText}>{i18n.t('common.retry')}</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <WebView
          source={{ uri: paymentUrl }}
          onLoadEnd={() => setLoading(false)}
          onError={() => { setLoading(false); setError(true); }}
          onNavigationStateChange={handleNavigationStateChange}
          javaScriptEnabled
          domStorageEnabled
          thirdPartyCookiesEnabled={false}   // PCI-DSS: restrict cross-site cookies
          style={styles.webview}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe:   { flex: 1, backgroundColor: colors.navy },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.offWhite, padding: spacing.lg },
  header: {
    flexDirection:    'row',
    alignItems:       'center',
    justifyContent:   'space-between',
    backgroundColor:  colors.navy,
    paddingHorizontal: spacing.md,
    paddingVertical:  spacing.sm,
    minHeight:        56,
  },
  headerLeft: { flex: 1 },
  headerTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize:   16,
    color:      colors.white,
  },
  headerSub: {
    fontFamily: 'Roboto_400Regular',
    fontSize:   11,
    color:      colors.teal,
    marginTop:  2,
  },
  cancelBtn: {
    paddingHorizontal: spacing.sm,
    paddingVertical:   spacing.xs,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelText: {
    fontFamily: 'Roboto_500Medium',
    fontSize:   14,
    color:      colors.error,
  },
  loadingOverlay: {
    position:       'absolute',
    top:            56,
    left:           0,
    right:          0,
    bottom:         0,
    alignItems:     'center',
    justifyContent: 'center',
    backgroundColor: colors.offWhite,
    zIndex:         10,
  },
  loadingText: {
    fontFamily: 'Roboto_400Regular',
    fontSize:   14,
    color:      colors.midGrey,
    marginTop:  spacing.sm,
  },
  webview: { flex: 1, backgroundColor: colors.offWhite },
  errorText: {
    fontFamily:  'Roboto_400Regular',
    fontSize:    16,
    color:       colors.error,
    textAlign:   'center',
    marginBottom: spacing.md,
  },
  backBtn: {
    backgroundColor: colors.teal,
    borderRadius:    8,
    paddingHorizontal: spacing.lg,
    paddingVertical:   12,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backBtnText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize:   15,
    color:      '#FFFFFF',
  },
});
