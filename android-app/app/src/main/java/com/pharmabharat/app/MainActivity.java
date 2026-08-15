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
                    bcConn.setConnectTimeout(6000);
                    bcConn.setReadTimeout(6000);
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

                        SharedPreferences prefs = getSharedPreferences("PharmlyPrefs", Context.MODE_PRIVATE);
                        String lastSavedBcId = prefs.getString("last_broadcast_notif_id", "");

                        if (!bcId.isEmpty() && !bcId.equals(lastSavedBcId) && !bcMsg.isEmpty()) {
                            prefs.edit().putString("last_broadcast_notif_id", bcId).apply();
                            NotificationHelper.showJobNotification(MainActivity.this, bcTitle, bcMsg);
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
                if (url.contains("pharmabharat-scraper-dic1.onrender.com") || url.contains("pharmabharat.com")) {
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
            NotificationHelper.showJobNotification(mContext, title, message);
        }

        @JavascriptInterface
        public void downloadAndInstallApk(final String apkUrl) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    try {
                        String fullUrl = apkUrl.startsWith("http") ? apkUrl : TARGET_URL + apkUrl;
                        java.net.URL url = new java.net.URL(fullUrl);
                        java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
                        conn.setRequestMethod("GET");
                        conn.setConnectTimeout(15000);
                        conn.setReadTimeout(15000);
                        conn.connect();

                        final int fileLength = conn.getContentLength();
                        java.io.File downloadDir = mContext.getExternalFilesDir(android.os.Environment.DIRECTORY_DOWNLOADS);
                        if (downloadDir != null && !downloadDir.exists()) downloadDir.mkdirs();
                        
                        final java.io.File apkFile = new java.io.File(downloadDir, "Pharmly_Update.apk");
                        downloadedApkFile = apkFile;

                        java.io.InputStream input = conn.getInputStream();
                        java.io.FileOutputStream output = new java.io.FileOutputStream(apkFile);

                        byte[] data = new byte[16384];
                        long total = 0;
                        int count;
                        long lastReportTime = 0;

                        while ((count = input.read(data)) != -1) {
                            total += count;
                            long currentTime = System.currentTimeMillis();
                            if (fileLength > 0 && (currentTime - lastReportTime > 200 || total == fileLength)) {
                                lastReportTime = currentTime;
                                final int progress = (int) (total * 100L / fileLength);
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
                        input.close();

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
