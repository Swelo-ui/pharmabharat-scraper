package com.pharmabharat.app;

import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;

public class BootReceiver extends BroadcastReceiver {

    public static final int JOB_ID = 9001;

    @Override
    public void onReceive(Context context, Intent intent) {
        scheduleJob(context);
    }

    public static void scheduleJob(Context context) {
        try {
            AlarmReceiver.scheduleAlarm(context);
            
            JobScheduler jobScheduler = (JobScheduler) context.getSystemService(Context.JOB_SCHEDULER_SERVICE);
            if (jobScheduler != null) {
                ComponentName componentName = new ComponentName(context, PharmaJobService.class);
                JobInfo jobInfo = new JobInfo.Builder(JOB_ID, componentName)
                        .setPeriodic(15 * 60 * 1000)
                        .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                        .setPersisted(true)
                        .build();
                jobScheduler.schedule(jobInfo);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
