package com.pharmabharat.app;

import android.app.Activity;
import android.os.Build;
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
import android.webkit.WebResourceResponse;
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
                String slug = null;
                if (targetUrl.startsWith("?job=")) {
                    slug = targetUrl.substring(5).trim();
                } else if (targetUrl.startsWith("/?job=")) {
                    slug = targetUrl.substring(6).trim();
                } else if (!targetUrl.contains("/") && !targetUrl.contains("?") && !targetUrl.contains("http")) {
                    slug = targetUrl.trim();
                }

                if (slug != null && !slug.isEmpty() && webView != null) {
                    String js = "if (typeof openJobModal === 'function') { openJobModal('" + slug + "'); } else { window.location.href = '" + TARGET_URL + "/?job=" + slug + "'; }";
                    webView.evaluateJavascript(js, null);
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

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setGeolocationEnabled(true);
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

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, android.webkit.GeolocationPermissions.Callback callback) {
                callback.invoke(origin, true, false);
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
                
                // Auto-rewrite any legacy / old render URL to the active dic1 URL
                if (url.contains("pharmabharat-scraper.onrender.com") && !url.contains("pharmabharat-scraper-dic1")) {
                    String correctedUrl = url.replace("pharmabharat-scraper.onrender.com", "pharmabharat-scraper-dic1.onrender.com");
                    view.loadUrl(correctedUrl);
                    return true;
                }

                // Keep internal app navigation within WebView (External links open in browser)
                Uri parsedUri = request.getUrl();
                String host = parsedUri != null ? parsedUri.getHost() : null;
                if (host != null && (host.equalsIgnoreCase("pharmabharat-scraper-dic1.onrender.com") 
                        || host.endsWith(".onrender.com")
                        || host.equalsIgnoreCase("localhost")
                        || host.equalsIgnoreCase("10.0.2.2"))) {
                    return false;
                }

                // External links (company career portals, pharmabharat, etc.) open in external browser
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                } catch (Exception e) {
                    return false;
                }
            }

            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (request != null && request.getUrl() != null) {
                    String reqUrl = request.getUrl().toString().toLowerCase();
                    if (reqUrl.contains("googlesyndication.com")
                            || reqUrl.contains("doubleclick.net")
                            || reqUrl.contains("pagead2")
                            || reqUrl.contains("adservice.google")
                            || reqUrl.contains("securepubads")
                            || reqUrl.contains("gpt.js")
                            || reqUrl.contains("adx")
                            || reqUrl.contains("taboola.com")
                            || reqUrl.contains("outbrain.com")
                            || reqUrl.contains("adnxs.com")) {
                        return new WebResourceResponse("text/plain", "UTF-8", new java.io.ByteArrayInputStream(new byte[0]));
                    }
                }
                return super.shouldInterceptRequest(view, request);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    showErrorScreen();
                }
            }

            private int serverErrorRetryCount = 0;

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse errorResponse) {
                if (request.isForMainFrame() && errorResponse != null) {
                    int statusCode = errorResponse.getStatusCode();
                    if (statusCode == 502 || statusCode == 503 || statusCode == 504) {
                        if (serverErrorRetryCount < 2) {
                            serverErrorRetryCount++;
                            view.postDelayed(new Runnable() {
                                @Override
                                public void run() {
                                    if (webView != null && isNetworkAvailable()) {
                                        webView.reload();
                                    }
                                }
                            }, 3500);
                            return;
                        }
                    }
                    if (statusCode >= 400) {
                        showErrorScreen();
                    }
                }
            }
        });
    }

    private void loadApp() {
        if (isNetworkAvailable()) {
            errorLayout.setVisibility(View.GONE);
            if (progressBar != null) {
                progressBar.setVisibility(View.VISIBLE);
                progressBar.setProgress(15);
            }
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

    private long lastBackPressTime = 0;

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        if (System.currentTimeMillis() - lastBackPressTime < 2000) {
            super.onBackPressed();
        } else {
            lastBackPressTime = System.currentTimeMillis();
            Toast.makeText(this, "Press back again to exit", Toast.LENGTH_SHORT).show();
        }
    }

    // JavaScript Interface to handle Share and Downloads from Web App
    public class WebAppInterface {
        Context mContext;

        WebAppInterface(Context c) {
            mContext = c;
        }

        @JavascriptInterface
        public void setSwipeRefreshEnabled(boolean enabled) {
            // Safe hook for web app calls
        }

        @JavascriptInterface
        public void setStatusBarColor(final String hexColor) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                            int color = android.graphics.Color.parseColor(hexColor);
                            getWindow().setStatusBarColor(color);
                            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                                double darkness = 1 - (0.299 * android.graphics.Color.red(color) + 0.587 * android.graphics.Color.green(color) + 0.114 * android.graphics.Color.blue(color)) / 255;
                                View decorView = getWindow().getDecorView();
                                int flags = decorView.getSystemUiVisibility();
                                if (darkness < 0.5) {
                                    flags |= View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
                                } else {
                                    flags &= ~View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
                                }
                                decorView.setSystemUiVisibility(flags);
                            }
                        }
                    } catch (Exception ignored) {}
                }
            });
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
                android.app.DownloadManager dm = (android.app.DownloadManager) mContext.getSystemService(Context.DOWNLOAD_SERVICE);
                if (dm != null) {
                    android.app.DownloadManager.Request req = new android.app.DownloadManager.Request(Uri.parse(fullUrl));
                    req.setAllowedNetworkTypes(android.app.DownloadManager.Request.NETWORK_WIFI | android.app.DownloadManager.Request.NETWORK_MOBILE);
                    req.setNotificationVisibility(android.app.DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    String safeName = (fileName != null && !fileName.trim().isEmpty()) ? fileName.trim() : "Pharmly_Flyer.jpg";
                    req.setTitle(safeName);
                    req.setDescription("Downloading recruitment flyer");
                    req.setDestinationInExternalPublicDir(android.os.Environment.DIRECTORY_DOWNLOADS, safeName);
                    dm.enqueue(req);
                    Toast.makeText(mContext, "Downloading flyer to Downloads...", Toast.LENGTH_SHORT).show();
                    return;
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            try {
                String fullUrl = fileUrl.startsWith("http") ? fileUrl : TARGET_URL + fileUrl;
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(fullUrl));
                mContext.startActivity(intent);
            } catch (Exception ex) {
                ex.printStackTrace();
            }
        }

        @JavascriptInterface
        public void showNativeNotification(String title, String message, String url) {
            NotificationHelper.showJobNotification(mContext, title, message, url);
        }

        @JavascriptInterface
        public void downloadAndInstallApk(final String apkUrl) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        String currentUrl = apkUrl != null && !apkUrl.isEmpty() ? apkUrl : "https://github.com/Swelo-ui/pharmabharat-scraper/releases/latest/download/Pharmly.apk";
                        if (!currentUrl.startsWith("http")) {
                            currentUrl = TARGET_URL + (currentUrl.startsWith("/") ? "" : "/") + currentUrl;
                        }
                        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(currentUrl));
                        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        mContext.startActivity(intent);
                        Toast.makeText(mContext, "Opening Pharmly download in browser...", Toast.LENGTH_SHORT).show();
                    } catch (Exception e) {
                        Toast.makeText(mContext, "Unable to launch browser download", Toast.LENGTH_SHORT).show();
                    }
                }
            });
        }

        @JavascriptInterface
        public void promptInstallApk() {
            downloadAndInstallApk("https://github.com/Swelo-ui/pharmabharat-scraper/releases/latest/download/Pharmly.apk");
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

        @JavascriptInterface
        public String getDeviceLocation() {
            try {
                android.location.LocationManager lm = (android.location.LocationManager) mContext.getSystemService(Context.LOCATION_SERVICE);
                if (lm != null) {
                    android.location.Location loc = null;
                    if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.M || 
                        mContext.checkSelfPermission(android.Manifest.permission.ACCESS_COARSE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                        loc = lm.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER);
                        if (loc == null && mContext.checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                            loc = lm.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER);
                        }
                    }
                    if (loc != null) {
                        android.location.Geocoder geocoder = new android.location.Geocoder(mContext, java.util.Locale.getDefault());
                        java.util.List<android.location.Address> list = geocoder.getFromLocation(loc.getLatitude(), loc.getLongitude(), 1);
                        if (list != null && !list.isEmpty()) {
                            android.location.Address addr = list.get(0);
                            String city = addr.getLocality();
                            if (city == null || city.isEmpty()) city = addr.getSubAdminArea();
                            String state = addr.getAdminArea();
                            return (city != null ? city : "") + "," + (state != null ? state : "");
                        }
                    }
                }
            } catch (Exception ignored) {}
            return "";
        }

        @JavascriptInterface
        public String getDeviceId() {
            try {
                SharedPreferences prefs = mContext.getSharedPreferences("pharmly_device_prefs", Context.MODE_PRIVATE);
                String id = prefs.getString("unique_device_id", null);
                if (id == null || id.isEmpty()) {
                    id = "phm-" + java.util.UUID.randomUUID().toString();
                    prefs.edit().putString("unique_device_id", id).apply();
                }
                return id;
            } catch (Exception e) {
                return "phm-" + java.util.UUID.randomUUID().toString();
            }
        }

        @JavascriptInterface
        public String getDeviceName() {
            try {
                String manufacturer = android.os.Build.MANUFACTURER;
                String model = android.os.Build.MODEL;
                if (manufacturer != null && model != null && model.toLowerCase().startsWith(manufacturer.toLowerCase())) {
                    return capitalize(model);
                } else if (manufacturer != null && model != null) {
                    return capitalize(manufacturer) + " " + model;
                } else {
                    return "Android Device";
                }
            } catch (Exception e) {
                return "Android Device";
            }
        }

        private String capitalize(String s) {
            if (s == null || s.length() == 0) return "";
            char first = s.charAt(0);
            if (Character.isUpperCase(first)) return s;
            return Character.toUpperCase(first) + s.substring(1);
        }

        @JavascriptInterface
        public String getOsVersion() {
            return "Android " + android.os.Build.VERSION.RELEASE + " (API " + android.os.Build.VERSION.SDK_INT + ")";
        }

        @JavascriptInterface
        public String getAppVersion() {
            try {
                android.content.pm.PackageInfo pInfo = mContext.getPackageManager().getPackageInfo(mContext.getPackageName(), 0);
                return pInfo.versionName;
            } catch (Exception e) {
                return "3.8.0";
            }
        }

        @JavascriptInterface
        public boolean isTestLab() {
            try {
                String testLab = android.provider.Settings.System.getString(mContext.getContentResolver(), "firebase.test.lab");
                if ("true".equalsIgnoreCase(testLab)) return true;
            } catch (Exception ignored) {}
            try {
                if ("true".equalsIgnoreCase(System.getProperty("firebase.test.lab"))) return true;
            } catch (Exception ignored) {}
            return false;
        }

    }
}
