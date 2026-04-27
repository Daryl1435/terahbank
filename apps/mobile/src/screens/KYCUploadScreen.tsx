/**
 * KYCUploadScreen — KYC document capture and upload.
 * Supports camera (expo-image-picker), gallery (expo-image-picker), and PDF (expo-document-picker).
 * Uploads via multipart FormData to POST /api/v1/users/me/kyc.
 * On success → KYCPending.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Alert,
  ScrollView,
  Image,
  StyleSheet,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { TerahButton } from '@/components/TerahButton';
import { colors } from '@/utils/tokens';
import { getAccessToken } from '@/stores/authStore';
import i18n from '@/locales';

type DocumentType = 'national_id' | 'passport' | 'residence_permit';

interface SelectedFile {
  uri: string;
  name: string;
  mimeType: string;
  isImage: boolean;
}

interface KYCUploadScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'KYCUpload'>;
}

const DOC_TYPES: { key: DocumentType; labelKey: string }[] = [
  { key: 'national_id',       labelKey: 'auth.kyc_doc_national_id' },
  { key: 'passport',          labelKey: 'auth.kyc_doc_passport' },
  { key: 'residence_permit',  labelKey: 'auth.kyc_doc_residence' },
];

export function KYCUploadScreen({ navigation }: KYCUploadScreenProps) {
  const [selectedType, setSelectedType] = useState<DocumentType>('national_id');
  const [file, setFile] = useState<SelectedFile | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const launchCamera = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') return;

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.85,
      allowsEditing: true,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setFile({
        uri: asset.uri,
        name: asset.fileName ?? `doc_${Date.now()}.jpg`,
        mimeType: asset.mimeType ?? 'image/jpeg',
        isImage: true,
      });
      setError(null);
    }
  };

  const launchGallery = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') return;

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.85,
      allowsEditing: true,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setFile({
        uri: asset.uri,
        name: asset.fileName ?? `doc_${Date.now()}.jpg`,
        mimeType: asset.mimeType ?? 'image/jpeg',
        isImage: true,
      });
      setError(null);
    }
  };

  const launchDocumentPicker = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: 'application/pdf',
      copyToCacheDirectory: true,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setFile({
        uri: asset.uri,
        name: asset.name,
        mimeType: asset.mimeType ?? 'application/pdf',
        isImage: false,
      });
      setError(null);
    }
  };

  const handlePickDocument = () => {
    Alert.alert(
      i18n.t('auth.kyc_pick_source_title'),
      undefined,
      [
        { text: i18n.t('auth.kyc_pick_camera'), onPress: launchCamera },
        { text: i18n.t('auth.kyc_pick_gallery'), onPress: launchGallery },
        { text: i18n.t('auth.kyc_pick_file'), onPress: launchDocumentPicker },
        { text: i18n.t('common.cancel'), style: 'cancel' },
      ],
    );
  };

  const handleUpload = async () => {
    if (!file) {
      setError(i18n.t('auth.kyc_no_file'));
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const token = await getAccessToken();
      const formData = new FormData();
      formData.append('document_type', selectedType);
      formData.append('file', {
        uri: file.uri,
        name: file.name,
        type: file.mimeType,
      } as any);

      const res = await fetch(
        `${process.env.EXPO_PUBLIC_API_BASE_URL}/api/v1/users/me/kyc`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        },
      );

      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.error?.message ?? i18n.t('errors.generic'));
      }

      navigation.navigate('KYCPending');
    } catch (err: any) {
      setError(err.message ?? i18n.t('errors.generic'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.container}>
      <Text style={styles.title}>{i18n.t('auth.kyc_upload_title')}</Text>
      <Text style={styles.subtitle}>{i18n.t('auth.kyc_upload_subtitle')}</Text>

      {/* Document type selector */}
      <View style={styles.typeRow}>
        {DOC_TYPES.map(({ key, labelKey }) => (
          <TouchableOpacity
            key={key}
            onPress={() => setSelectedType(key)}
            accessibilityRole="radio"
            accessibilityState={{ selected: selectedType === key }}
            style={[styles.typeChip, selectedType === key && styles.typeChipSelected]}
          >
            <Text style={[styles.typeChipText, selectedType === key && styles.typeChipTextSelected]}>
              {i18n.t(labelKey)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Pick area */}
      <TouchableOpacity
        onPress={handlePickDocument}
        accessibilityRole="button"
        accessibilityLabel={i18n.t('auth.kyc_pick_prompt')}
        style={[styles.pickArea, file && styles.pickAreaSelected]}
      >
        {file?.isImage && file.uri ? (
          <Image source={{ uri: file.uri }} style={styles.previewImage} resizeMode="cover" />
        ) : (
          <>
            <Text style={styles.pickIcon}>{file ? '📄' : '📷'}</Text>
            <Text style={styles.pickText}>
              {file ? i18n.t('auth.kyc_pick_change') : i18n.t('auth.kyc_pick_prompt')}
            </Text>
            {file && !file.isImage ? (
              <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
            ) : null}
          </>
        )}
      </TouchableOpacity>

      {error ? (
        <Text style={styles.errorText} accessibilityRole="alert">
          {error}
        </Text>
      ) : null}

      <TerahButton
        label={i18n.t('auth.kyc_submit')}
        onPress={handleUpload}
        loading={uploading}
        disabled={!file}
        style={styles.submitButton}
      />
    </ScrollView>
  );
}

export default KYCUploadScreen;

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    paddingHorizontal: 24,
    paddingTop: 40,
    paddingBottom: 32,
  },
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 8,
  },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.darkGrey,
    lineHeight: 24,
    marginBottom: 28,
  },
  typeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 24,
  },
  typeChip: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 999,
    borderWidth: 1.5,
    borderColor: colors.lightGrey,
    backgroundColor: '#FFFFFF',
  },
  typeChipSelected: {
    borderColor: colors.teal,
    backgroundColor: colors.teal,
  },
  typeChipText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.darkGrey,
  },
  typeChipTextSelected: {
    color: '#FFFFFF',
    fontFamily: 'Roboto_500Medium',
  },
  pickArea: {
    borderWidth: 2,
    borderColor: colors.lightGrey,
    borderStyle: 'dashed',
    borderRadius: 12,
    padding: 32,
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    marginBottom: 16,
    minHeight: 140,
    justifyContent: 'center',
    overflow: 'hidden',
  },
  pickAreaSelected: {
    borderColor: colors.teal,
    borderStyle: 'solid',
    padding: 0,
  },
  previewImage: {
    width: '100%',
    height: 180,
    borderRadius: 10,
  },
  pickIcon: {
    fontSize: 36,
    marginBottom: 10,
  },
  pickText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
    textAlign: 'center',
    lineHeight: 20,
  },
  fileName: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 13,
    color: colors.teal,
    marginTop: 6,
    maxWidth: '90%',
  },
  errorText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.error,
    marginBottom: 12,
    textAlign: 'center',
  },
  submitButton: {
    marginTop: 8,
  },
});
