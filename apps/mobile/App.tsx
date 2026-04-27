import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useFonts,
  Poppins_400Regular,
  Poppins_500Medium,
  Poppins_600SemiBold,
  Poppins_700Bold,
} from '@expo-google-fonts/poppins';
import { Roboto_400Regular, Roboto_500Medium } from '@expo-google-fonts/roboto';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { useAuthStore } from '@/stores/authStore';
import { colors } from '@/utils/tokens';

// ── Auth & onboarding screens ──────────────────────────────────────────────────
import LoginScreen from '@/screens/LoginScreen';
import RegisterScreen from '@/screens/RegisterScreen';
import PasswordCreationScreen from '@/screens/PasswordCreationScreen';
import OTPScreen from '@/screens/OTPScreen';
import PINSetupScreen from '@/screens/PINSetupScreen';
import BiometricSetupScreen from '@/screens/BiometricSetupScreen';
import DeviceVerificationScreen from '@/screens/DeviceVerificationScreen';
import KYCUploadScreen from '@/screens/KYCUploadScreen';
import KYCPendingScreen from '@/screens/KYCPendingScreen';

// ── Authenticated app screens ─────────────────────────────────────────────────
import DashboardScreen from '@/screens/DashboardScreen';
import AccountDetailScreen from '@/screens/AccountDetailScreen';
import ProfileScreen from '@/screens/ProfileScreen';

// ── Account creation flows ────────────────────────────────────────────────────
import OpenAccountScreen from '@/screens/OpenAccountScreen';
import OpenStandardAccountScreen from '@/screens/OpenStandardAccountScreen';
import OpenProjectAccountScreen from '@/screens/OpenProjectAccountScreen';
import OpenTermDepositScreen from '@/screens/OpenTermDepositScreen';

// ── Transaction flows — Milestone 3.5 ────────────────────────────────────────
import DepositScreen from '@/screens/DepositScreen';
import WithdrawScreen from '@/screens/WithdrawScreen';
import TransferScreen from '@/screens/TransferScreen';
import TransactionHistoryScreen from '@/screens/TransactionHistoryScreen';
import TransactionDetailScreen from '@/screens/TransactionDetailScreen';

// ── Card management — Milestone 3.4 / 4.2 ────────────────────────────────────
import CardScreen from '@/screens/CardScreen';
import CardDetailScreen from '@/screens/CardDetailScreen';
import CardPaymentWebViewScreen from '@/screens/CardPaymentWebViewScreen';

// ── Insurance — Milestone 6.1 ─────────────────────────────────────────────────
import InsuranceScreen from '@/screens/InsuranceScreen';
import InsurancePolicyDetailScreen from '@/screens/InsurancePolicyDetailScreen';

// ─── Navigation types ─────────────────────────────────────────────────────────

export type RootStackParamList = {
  // Auth
  Login: undefined;
  Register: undefined;
  PasswordCreation: {
    full_name: string;
    phone_number: string;
    email: string;
    city?: string;
    address?: string;
  };
  OTP: { userId: string; purpose: 'verify' | 'login' };
  PINSetup: undefined;
  BiometricSetup: undefined;
  DeviceVerification: { userId: string; kycStatus: string };
  KYCUpload: undefined;
  KYCPending: undefined;

  // App
  Dashboard: undefined;
  AccountDetail: { accountId: string };
  Profile: undefined;
  Notifications: undefined;       // Stub — Milestone 6

  // Account creation flows
  OpenAccount: undefined;
  OpenStandardAccount: undefined;
  OpenProjectAccount: undefined;
  OpenTermDeposit: undefined;

  // Transaction flows — Milestone 3.5
  Deposit: undefined;
  Withdraw: undefined;
  Transfer: undefined;
  TransactionHistory: { accountId?: string };
  TransactionDetail: { transactionId: string; reference: string };

  // Card management — Milestone 3.4 / 4.2
  Cards: undefined;
  CardDetail: { cardId: string };
  CardPaymentWebView: { paymentUrl: string; transactionId: string; reference: string };

  // Insurance — Milestone 6.1
  Insurance: undefined;
  InsurancePolicyDetail: { policyId: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

// ─── React Query client ───────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,        // 30s — aligns with Redis balance cache TTL
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,                 // Never auto-retry mutations (double-charge risk)
    },
  },
});

// ─── Navigation tree ──────────────────────────────────────────────────────────

function AppNavigator() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const kycStatus       = useAuthStore((s) => s.kycStatus);

  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.offWhite },
        animation: 'slide_from_right',
      }}
    >
      {!isAuthenticated ? (
        // ── Auth + onboarding stack ─────────────────────────────────────────
        <>
          <Stack.Screen name="Login"              component={LoginScreen} />
          <Stack.Screen name="Register"           component={RegisterScreen} />
          <Stack.Screen name="PasswordCreation"   component={PasswordCreationScreen} />
          <Stack.Screen name="OTP"                component={OTPScreen} />
          <Stack.Screen name="PINSetup"           component={PINSetupScreen} />
          <Stack.Screen name="BiometricSetup"     component={BiometricSetupScreen} />
          <Stack.Screen name="DeviceVerification" component={DeviceVerificationScreen} />
          <Stack.Screen name="KYCUpload"          component={KYCUploadScreen} />
          <Stack.Screen name="KYCPending"         component={KYCPendingScreen} />
        </>
      ) : kycStatus !== 'approved' ? (
        // ── KYC gate — block until KYC is approved ──────────────────────────
        <>
          <Stack.Screen name="KYCUpload"  component={KYCUploadScreen} />
          <Stack.Screen name="KYCPending" component={KYCPendingScreen} />
        </>
      ) : (
        // ── Authenticated app ───────────────────────────────────────────────
        <>
          <Stack.Screen name="Dashboard"            component={DashboardScreen} />
          <Stack.Screen name="AccountDetail"        component={AccountDetailScreen} />
          <Stack.Screen name="Profile"              component={ProfileScreen} />
          {/* Account creation flows */}
          <Stack.Screen name="OpenAccount"          component={OpenAccountScreen} />
          <Stack.Screen name="OpenStandardAccount"  component={OpenStandardAccountScreen} />
          <Stack.Screen name="OpenProjectAccount"   component={OpenProjectAccountScreen} />
          <Stack.Screen name="OpenTermDeposit"      component={OpenTermDepositScreen} />
          {/* Transaction flows — Milestone 3.5 */}
          <Stack.Screen name="Deposit"             component={DepositScreen} />
          <Stack.Screen name="Withdraw"            component={WithdrawScreen} />
          <Stack.Screen name="Transfer"            component={TransferScreen} />
          <Stack.Screen name="TransactionHistory"  component={TransactionHistoryScreen} />
          <Stack.Screen name="TransactionDetail"   component={TransactionDetailScreen} />
          {/* Card management — Milestone 3.4 / 4.2 */}
          <Stack.Screen name="Cards"               component={CardScreen} />
          <Stack.Screen name="CardDetail"          component={CardDetailScreen} />
          <Stack.Screen name="CardPaymentWebView"  component={CardPaymentWebViewScreen} options={{ gestureEnabled: false }} />
          {/* Insurance — Milestone 6.1 */}
          <Stack.Screen name="Insurance"              component={InsuranceScreen} />
          <Stack.Screen name="InsurancePolicyDetail"  component={InsurancePolicyDetailScreen} />
          {/* Notifications stub — Milestone 6 */}
          <Stack.Screen name="Notifications"          component={DashboardScreen} />
        </>
      )}
    </Stack.Navigator>
  );
}

// ─── Root component ───────────────────────────────────────────────────────────

export default function App() {
  const [fontsLoaded, fontError] = useFonts({
    Poppins_400Regular,
    Poppins_500Medium,
    Poppins_600SemiBold,
    Poppins_700Bold,
    Roboto_400Regular,
    Roboto_500Medium,
  });

  if (!fontsLoaded && !fontError) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.navy }}>
        <ActivityIndicator size="large" color={colors.teal} />
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <StatusBar style="light" backgroundColor={colors.navy} />
          <NavigationContainer>
            <AppNavigator />
          </NavigationContainer>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
