import { useRef, useState, useCallback } from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View, BackHandler, ActivityIndicator, Text, SafeAreaView } from 'react-native';
import { WebView } from 'react-native-webview';
import { useEffect } from 'react';

// The whole app lives on Railway — this is just a thin native shell around it.
// Update the deployed site any time; nothing here needs to change or rebuild.
const APP_URL = 'https://jlc-textile-production.up.railway.app';

export default function App() {
  const webviewRef = useRef(null);
  const [canGoBack, setCanGoBack] = useState(false);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const onBackPress = () => {
      if (canGoBack && webviewRef.current) {
        webviewRef.current.goBack();
        return true;
      }
      return false; // let Android's default back action (exit app) happen
    };
    const sub = BackHandler.addEventListener('hardwareBackPress', onBackPress);
    return () => sub.remove();
  }, [canGoBack]);

  const retry = useCallback(() => {
    setError(false);
    setLoading(true);
    webviewRef.current?.reload();
  }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" backgroundColor="#1C1C1E" />
      {error ? (
        <View style={styles.center}>
          <Text style={styles.errorTitle}>Couldn't connect</Text>
          <Text style={styles.errorBody}>Check your internet connection and try again.</Text>
          <Text style={styles.retry} onPress={retry}>Tap to retry</Text>
        </View>
      ) : (
        <WebView
          ref={webviewRef}
          source={{ uri: APP_URL }}
          style={styles.webview}
          onNavigationStateChange={(nav) => setCanGoBack(nav.canGoBack)}
          onLoadEnd={() => setLoading(false)}
          onError={() => { setError(true); setLoading(false); }}
          onHttpError={(e) => {
            // 401s during login flows are normal — only treat hard failures as fatal.
            if (e.nativeEvent.statusCode >= 500) setError(true);
          }}
          startInLoadingState
          renderLoading={() => (
            <View style={[styles.center, styles.loadingOverlay]}>
              <ActivityIndicator size="large" color="#5E7E9B" />
            </View>
          )}
          pullToRefreshEnabled
          domStorageEnabled
          javaScriptEnabled
          allowsBackForwardNavigationGestures
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#1C1C1E' },
  webview: { flex: 1, backgroundColor: '#1C1C1E' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#1C1C1E', padding: 24 },
  loadingOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 },
  errorTitle: { color: '#fff', fontSize: 18, fontWeight: '700', marginBottom: 8 },
  errorBody: { color: '#9B9BA1', fontSize: 14, textAlign: 'center', marginBottom: 16 },
  retry: { color: '#5E7E9B', fontSize: 15, fontWeight: '600' },
});
