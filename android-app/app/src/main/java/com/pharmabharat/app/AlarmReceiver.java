package com.pharmabharat.app;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.PowerManager;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class AlarmReceiver extends BroadcastReceiver {

    public static final int ALARM_REQ_CODE = 8001;
    private static final String PREFS_NAME = "PharmlyPrefs";
    private static final String KEY_LAST_JOB_ID = "last_job_id";
    private static final long INTERVAL_MS = 5 * 60 * 1000; // 5 minutes fast background check

    @Override
    public void onReceive(final Context context, Intent intent) {
        // Reschedule next alarm immediately so polling continues indefinitely in background
        scheduleAlarm(context);

        // Acquire temporary wake lock to complete background check even in Doze mode
        PowerManager pm = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
        final PowerManager.WakeLock wakeLock = pm != null ? pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Pharmly:NotifWakeLock") : null;
        if (wakeLock != null) {
            try {
                wakeLock.acquire(30000); // 30s timeout safety
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    URL url = new URL("https://pharmabharat-scraper.onrender.com/api/jobs?per_page=5");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("GET");
                    conn.setConnectTimeout(12000);
                    conn.setReadTimeout(12000);

                    if (conn.getResponseCode() == 200) {
                        BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                        StringBuilder sb = new StringBuilder();
                        String line;
                        while ((line = reader.readLine()) != null) {
                            sb.append(line);
                        }
                        reader.close();

                        JSONObject json = new JSONObject(sb.toString());
                        JSONArray jobs = json.optJSONArray("jobs");
                        if (jobs != null && jobs.length() > 0) {
                            JSONObject latestJob = jobs.getJSONObject(0);
                            String latestSlug = latestJob.optString("slug", "");
                            String latestTitle = latestJob.optString("title", "New Job Opening").trim();
                            String latestCompany = latestJob.optString("company", "").trim();
                            String latestLoc = latestJob.optString("location", "").trim();

                            if (latestCompany.equalsIgnoreCase("null") || latestCompany.equalsIgnoreCase("none")) {
                                latestCompany = "";
                            }
                            if (latestLoc.equalsIgnoreCase("null") || latestLoc.equalsIgnoreCase("none")) {
                                latestLoc = "";
                            }

                            SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
                            String lastSavedSlug = prefs.getString(KEY_LAST_JOB_ID, "");

                            if (!latestSlug.isEmpty() && !latestSlug.equals(lastSavedSlug)) {
                                prefs.edit().putString(KEY_LAST_JOB_ID, latestSlug).apply();

                                String notifTitle = "Pharmly Job Alert";
                                StringBuilder sbMsg = new StringBuilder();
                                sbMsg.append(latestTitle);
                                if (!latestCompany.isEmpty()) {
                                    sbMsg.append(" — ").append(latestCompany);
                                }
                                if (!latestLoc.isEmpty()) {
                                    sbMsg.append(" (").append(latestLoc).append(")");
                                }
                                String notifMsg = sbMsg.toString();
                                NotificationHelper.showJobNotification(context, notifTitle, notifMsg);
                            }
                        }
                    }

                    // ─── Background App Version Update Check ───
                    try {
                        URL verUrl = new URL("https://pharmabharat-scraper.onrender.com/api/app-version");
                        HttpURLConnection verConn = (HttpURLConnection) verUrl.openConnection();
                        verConn.setRequestMethod("GET");
                        verConn.setConnectTimeout(8000);
                        verConn.setReadTimeout(8000);
                        if (verConn.getResponseCode() == 200) {
                            BufferedReader r = new BufferedReader(new InputStreamReader(verConn.getInputStream()));
                            StringBuilder sbVer = new StringBuilder();
                            String l;
                            while ((l = r.readLine()) != null) sbVer.append(l);
                            r.close();

                            JSONObject vJson = new JSONObject(sbVer.toString());
                            int serverCode = vJson.optInt("version_code", 1);
                            String verName = vJson.optString("version_name", "3.2");

                            SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
                            int lastNotifiedCode = prefs.getInt("last_notified_ver_code", 0);
                            int currentCode = 1;
                            try {
                                currentCode = context.getPackageManager().getPackageInfo(context.getPackageName(), 0).versionCode;
                            } catch (Exception ignored) {}

                            if (serverCode > currentCode && serverCode > lastNotifiedCode) {
                                prefs.edit().putInt("last_notified_ver_code", serverCode).apply();
                                String notifTitle = "Pharmly Update Available (v" + verName + ")";
                                String notifMsg = "A new version of Pharmly is ready. Tap to install now!";
                                NotificationHelper.showJobNotification(context, notifTitle, notifMsg);
                            }
                        }
                    } catch (Exception ignored) {}

                    // ─── Broadcast Custom Push Notification Check ───
                    try {
                        URL bcUrl = new URL("https://pharmabharat-scraper.onrender.com/api/push-broadcast");
                        HttpURLConnection bcConn = (HttpURLConnection) bcUrl.openConnection();
                        bcConn.setRequestMethod("GET");
                        bcConn.setConnectTimeout(8000);
                        bcConn.setReadTimeout(8000);
                        if (bcConn.getResponseCode() == 200) {
                            BufferedReader r = new BufferedReader(new InputStreamReader(bcConn.getInputStream()));
                            StringBuilder sbBc = new StringBuilder();
                            String l;
                            while ((l = r.readLine()) != null) sbBc.append(l);
                            r.close();

                            JSONObject bcJson = new JSONObject(sbBc.toString());
                            String bcId = bcJson.optString("id", "");
                            String bcTitle = bcJson.optString("title", "Pharmly Notification");
                            String bcMsg = bcJson.optString("message", "");

                            SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
                            String lastSavedBcId = prefs.getString("last_broadcast_notif_id", "");

                            if (!bcId.isEmpty() && !bcId.equals(lastSavedBcId) && !bcMsg.isEmpty()) {
                                prefs.edit().putString("last_broadcast_notif_id", bcId).apply();
                                NotificationHelper.showJobNotification(context, bcTitle, bcMsg);
                            }
                        }
                    } catch (Exception ignored) {}

                } catch (Exception e) {
                    e.printStackTrace();
                } finally {
                    if (wakeLock != null && wakeLock.isHeld()) {
                        try {
                            wakeLock.release();
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                }
            }
        }).start();
    }

    public static void scheduleAlarm(Context context) {
        try {
            AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            if (alarmManager != null) {
                Intent intent = new Intent(context, AlarmReceiver.class);
                PendingIntent pendingIntent = PendingIntent.getBroadcast(
                        context,
                        ALARM_REQ_CODE,
                        intent,
                        PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                );

                long triggerAt = System.currentTimeMillis() + INTERVAL_MS;
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pendingIntent);
                } else {
                    alarmManager.setExact(AlarmManager.RTC_WAKEUP, triggerAt, pendingIntent);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
