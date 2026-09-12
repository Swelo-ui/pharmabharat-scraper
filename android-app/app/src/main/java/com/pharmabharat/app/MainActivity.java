package com.pharmabharat.app;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.Toast;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import java.io.File;
import androidx.core.app.NotificationCompat;

public class MainActivity extends Activity {

    private static final String TARGET_URL = "https://pharmabharat-scraper-dic1.onrender.com";

    private WebView webView;
    private ProgressBar progressBar;
    private LinearLayout errorLayout;
    private Button btnRetry;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webView);
        progressBar = findViewById(R.id.progressBar);
        errorLayout = findViewById(R.id.errorLayout);
        btnRetry = findViewById(R.id.btnRetry);

        setupWebView();

        btnRetry.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                loadApp();
            }
        });

        loadApp();
        handleIncomingIntent(getIntent());
        BootReceiver.scheduleJob(this);
        checkInstantBroadcastNotification();

        // Request runtime notification permission for Android 13+ (API 33+)
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            if (checkSelfPermission("android.permission.POST_NOTIFICATIONS") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, 101);
            }
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIncomingIntent(intent);
    }

    private void handleIncomingIntent(Intent intent) {
        if (intent == null) return;
        String targetUrl = intent.getStringExtra("target_url");
        if (targetUrl != null && !targetUrl.trim().isEmpty()) {
            targetUrl = targetUrl.trim();
            if ("update".equalsIgnoreCase(targetUrl)) {
                if (webView != null) {
                    webView.evaluateJavascript("if(typeof triggerInAppUpdate === 'function') triggerInAppUpdate(); else if(typeof checkAppUpdate === 'function') checkAppUpdate();", null);
                }
            } else {
                String fullTarget;
                if (targetUrl.startsWith("http://") || targetUrl.startsWith("https://")) {
                    fullTarget = targetUrl;
                } else if (targetUrl.startsWith("?")) {
                    fullTarget = TARGET_URL + "/" + targetUrl;
                } else if (targetUrl.startsWith("/")) {
                    fullTarget = TARGET_URL + targetUrl;
                } else {
                    fullTarget = TARGET_URL + "/?job=" + targetUrl;
                }
                if (webView != null) {
                    webView.loadUrl(fullTarget);
                }
            }
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.loadUrl("about:blank");
            webView.stopLoading();
            webView.setWebChromeClient(null);
            webView.setWebViewClient(null);
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    @Override
    protected void onResume() {
        super.onResume();
        checkInstantBroadcastNotification();
    }

    private void checkInstantBroadcastNotification() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    java.net.URL bcUrl = new java.net.URL("https://pharmabharat-scraper-dic1.onrender.com/api/push-broadcast");
                    java.net.HttpURLConnection bcConn = (java.net.HttpURLConnection) bcUrl.openConnection();
                    bcConn.setRequestMethod("GET");
                    bcConn.setConnectTimeout(15000);
                    bcConn.setReadTimeout(15000);
                    if (bcConn.getResponseCode() == 200) {
                        java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(bcConn.getInputStream()));
                        StringBuilder sbBc = new StringBuilder();
                        String l;
                        while ((l = r.readLine()) != null) sbBc.append(l);
                        r.close();

                        org.json.JSONObject bcJson = new org.json.JSONObject(sbBc.toString());
                        if (bcJson.has("notification") && !bcJson.isNull("notification")) {
                            bcJson = bcJson.getJSONObject("notification");
                        }
                        final String bcId = bcJson.optString("id", "");
                        final String bcTitle = bcJson.optString("title", "");
                        final String bcMsg = bcJson.optString("message", "");
                        final String bcTarget = bcJson.optString("url", "");

                        SharedPreferences prefs = getSharedPreferences("PharmlyPrefs", Context.MODE_PRIVATE);
                        String lastSavedBcId = prefs.getString("last_broadcast_notif_id", "");

                        if (!bcId.isEmpty() && !bcId.equals(lastSavedBcId) && !bcMsg.isEmpty()) {
                            prefs.edit().putString("last_broadcast_notif_id", bcId).apply();
                            NotificationHelper.showJobNotification(MainActivity.this, bcTitle, bcMsg, bcTarget);
                        }
                    }
                } catch (Exception ignored) {}
            }
        }).start();
    }

    private File downloadedApkFile = null;

    private void installApkFileDirect(Context context, File apkFile) {
        if (apkFile == null || !apkFile.exists()) return;
        try {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                if (!context.getPackageManager().canRequestPackageInstalls()) {
                    Toast.makeText(context, "Please allow Pharmly to install app updates", Toast.LENGTH_LONG).show();
                    Intent settingsIntent = new Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES);
                    settingsIntent.setData(Uri.parse("package:" + context.getPackageName()));
                    settingsIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    context.startActivity(settingsIntent);
                    return;
                }
            }

            Uri apkUri;
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.N) {
                apkUri = androidx.core.content.FileProvider.getUriForFile(
                    context,
                    context.getPackageName() + ".fileprovider",
                    apkFile
                );
            } else {
                apkUri = Uri.fromFile(apkFile);
            }

            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(apkUri, "application/vnd.android.package-archive");
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            context.startActivity(intent);
        } catch (Exception e) {
            e.printStackTrace();
            Toast.makeText(context, "Installation failed: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);

        // Hardware Acceleration
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);

        // Register Javascript Interface for Native Android Features (Share, Download, Toast)
        webView.addJavascriptInterface(new WebAppInterface(this), "AndroidNative");

        // Set Download Listener for Excel/CSV file downloads
        webView.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition, String mimetype, long contentLength) {
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Downloading file...", Toast.LENGTH_SHORT).show();
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (newProgress < 100) {
                    progressBar.setVisibility(View.VISIBLE);
                    progressBar.setProgress(newProgress);
                } else {
                    progressBar.setVisibility(View.GONE);
                }
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();

                // Handle export downloads in browser/intent
                if (url.contains("/api/export")) {
                    try {
                        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                        startActivity(intent);
                        return true;
                    } catch (Exception e) {
                        return false;
                    }
                }
                
                // Handle mailto links via ACTION_SENDTO so mail app opens directly without password prompts
                if (url.startsWith("mailto:")) {
                    try {
                        Intent intent = new Intent(Intent.ACTION_SENDTO);
                        intent.setData(Uri.parse(url));
                        startActivity(intent);
                        return true;
                    } catch (Exception e) {
                        try {
                            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                            startActivity(intent);
                            return true;
                        } catch (Exception ex) {
                            return false;
                        }
                    }
                }

                // Handle tel links via ACTION_DIAL
                if (url.startsWith("tel:")) {
                    try {
                        Intent intent = new Intent(Intent.ACTION_DIAL, Uri.parse(url));
                        startActivity(intent);
                        return true;
                    } catch (Exception e) {
                        return false;
                    }
                }

                // Handle whatsapp links
                if (url.startsWith("whatsapp:") || url.startsWith("https://wa.me/")) {
                    try {
                        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                        startActivity(intent);
                        return true;
                    } catch (Exception e) {
                        return false;
                    }
                }
                
                // Keep internal app navigation within WebView
                Uri parsedUri = request.getUrl();
                String host = parsedUri != null ? parsedUri.getHost() : null;
                if (host != null && (host.equalsIgnoreCase("pharmabharat-scraper-dic1.onrender.com") 
                        || host.equalsIgnoreCase("pharmabharat.com") 
                        || host.endsWith(".pharmabharat.com")
                        || host.endsWith(".onrender.com"))) {
                    return false;
                }

                // External links open in device browser
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                } catch (Exception e) {
                    return false;
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    showErrorScreen();
                }
            }
        });
    }

    private void loadApp() {
        if (isNetworkAvailable()) {
            errorLayout.setVisibility(View.GONE);
            webView.setVisibility(View.VISIBLE);
            webView.loadUrl(TARGET_URL);
        } else {
            showErrorScreen();
        }
    }

    private void showErrorScreen() {
        webView.setVisibility(View.GONE);
        progressBar.setVisibility(View.GONE);
        errorLayout.setVisibility(View.VISIBLE);
    }

    private boolean isNetworkAvailable() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (cm != null) {
            NetworkInfo activeNetwork = cm.getActiveNetworkInfo();
            return activeNetwork != null && activeNetwork.isConnectedOrConnecting();
        }
        return false;
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    // JavaScript Interface to handle Share and Downloads from Web App
    public class WebAppInterface {
        Context mContext;

        WebAppInterface(Context c) {
            mContext = c;
        }

        @JavascriptInterface
        public void shareText(String title, String text) {
            try {
                Intent sendIntent = new Intent();
                sendIntent.setAction(Intent.ACTION_SEND);
                sendIntent.putExtra(Intent.EXTRA_TEXT, text);
                sendIntent.setType("text/plain");
                Intent shareIntent = Intent.createChooser(sendIntent, title);
                mContext.startActivity(shareIntent);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        @JavascriptInterface
        public void downloadFile(String fileUrl, String fileName) {
            try {
                String fullUrl = fileUrl.startsWith("http") ? fileUrl : TARGET_URL + fileUrl;
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(fullUrl));
                mContext.startActivity(intent);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        @JavascriptInterface
        public void showNativeNotification(String title, String message, String url) {
            NotificationHelper.showJobNotification(mContext, title, message, url);
        }

        @JavascriptInterface
        public void downloadAndInstallApk(final String apkUrl) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    java.io.InputStream input = null;
                    java.io.FileOutputStream output = null;
                    try {
                        String currentUrl = apkUrl.startsWith("http") ? apkUrl : TARGET_URL + apkUrl;
                        Uri checkUri = Uri.parse(currentUrl);
                        String checkHost = checkUri.getHost();
                        if (checkHost == null || (!checkHost.contains("github") && !checkHost.contains("onrender") && !checkHost.contains("pharmabharat"))) {
                            throw new SecurityException("Untrusted download source: " + checkHost);
                        }

                        // Follow redirects safely (handles GitHub Releases -> AWS S3 / Azure CDN)
                        java.net.HttpURLConnection conn = null;
                        int redirects = 0;
                        while (redirects < 6) {
                            java.net.URL u = new java.net.URL(currentUrl);
                            conn = (java.net.HttpURLConnection) u.openConnection();
                            conn.setRequestMethod("GET");
                            conn.setConnectTimeout(25000);
                            conn.setReadTimeout(25000);
                            conn.setInstanceFollowRedirects(false);
                            conn.setRequestProperty("User-Agent", "Pharmly-Android/" + getAppVersionCode());
                            conn.connect();

                            int status = conn.getResponseCode();
                            if (status == 301 || status == 302 || status == 303 || status == 307 || status == 308) {
                                String redirectUrl = conn.getHeaderField("Location");
                                if (redirectUrl != null) {
                                    if (!redirectUrl.startsWith("http")) {
                                        redirectUrl = new java.net.URL(u, redirectUrl).toExternalForm();
                                    }
                                    currentUrl = redirectUrl;
                                    redirects++;
                                    conn.disconnect();
                                    continue;
                                }
                            }
                            break;
                        }

                        if (conn == null || conn.getResponseCode() != 200) {
                            int code = conn != null ? conn.getResponseCode() : -1;
                            throw new java.io.IOException("Server returned HTTP " + code);
                        }

                        final int fileLength = conn.getContentLength();
                        java.io.File downloadDir = mContext.getExternalFilesDir(android.os.Environment.DIRECTORY_DOWNLOADS);
                        if (downloadDir != null && !downloadDir.exists()) downloadDir.mkdirs();
                        
                        final java.io.File apkFile = new java.io.File(downloadDir, "Pharmly_Update.apk");
                        downloadedApkFile = apkFile;

                        input = conn.getInputStream();
                        output = new java.io.FileOutputStream(apkFile);

                        byte[] data = new byte[16384];
                        long total = 0;
                        int count;
                        long lastReportTime = 0;

                        while ((count = input.read(data)) != -1) {
                            total += count;
                            long currentTime = System.currentTimeMillis();
                            if (fileLength > 0 && (currentTime - lastReportTime > 150 || total == fileLength)) {
                                lastReportTime = currentTime;
                                final int progress = Math.min(100, (int) (total * 100L / fileLength));
                                runOnUiThread(new Runnable() {
                                    @Override
                                    public void run() {
                                        if (webView != null) {
                                            webView.evaluateJavascript("if(window.onApkDownloadProgress) window.onApkDownloadProgress(" + progress + ");", null);
                                        }
                                    }
                                });
                            }
                            output.write(data, 0, count);
                        }

                        output.flush();
                        output.close();
                        output = null;
                        input.close();
                        input = null;

                        // Download Complete -> Update UI to 100% and launch package installer immediately!
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                if (webView != null) {
                                    webView.evaluateJavascript("if(window.onApkDownloadComplete) window.onApkDownloadComplete();", null);
                                }
                                installApkFileDirect(mContext, apkFile);
                            }
                        });

                    } catch (final Exception e) {
                        e.printStackTrace();
                        try { if (output != null) output.close(); } catch (Exception ignored) {}
                        try { if (input != null) input.close(); } catch (Exception ignored) {}
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                Toast.makeText(mContext, "Download failed! Opening in browser...", Toast.LENGTH_SHORT).show();
                                try {
                                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(apkUrl));
                                    mContext.startActivity(intent);
                                } catch(Exception ignored){}
                            }
                        });
                    }
                }
            }).start();
        }

        @JavascriptInterface
        public void promptInstallApk() {
            if (downloadedApkFile != null && downloadedApkFile.exists()) {
                installApkFileDirect(mContext, downloadedApkFile);
            }
        }

        @JavascriptInterface
        public int getAppVersionCode() {
            try {
                android.content.pm.PackageInfo pInfo = mContext.getPackageManager().getPackageInfo(mContext.getPackageName(), 0);
                return pInfo.versionCode;
            } catch (Exception e) {
                return 1;
            }
        }
    }
}
