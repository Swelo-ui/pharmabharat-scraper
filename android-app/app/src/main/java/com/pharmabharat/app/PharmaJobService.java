package com.pharmabharat.app;

import android.app.job.JobParameters;
import android.app.job.JobService;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class PharmaJobService extends JobService {

    private static final String PREFS_NAME = "PharmlyPrefs";
    private static final String KEY_LAST_JOB_ID = "last_job_id";

    @Override
    public boolean onStartJob(final JobParameters params) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    URL url = new URL("https://pharmabharat-scraper-y2g3.onrender.com/api/jobs?per_page=5");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("GET");
                    conn.setConnectTimeout(10000);
                    conn.setReadTimeout(10000);

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

                            SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
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
                                NotificationHelper.showJobNotification(getApplicationContext(), notifTitle, notifMsg);
                            }
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                } finally {
                    jobFinished(params, false);
                }
            }
        }).start();
        return true;
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        return true;
    }
}
