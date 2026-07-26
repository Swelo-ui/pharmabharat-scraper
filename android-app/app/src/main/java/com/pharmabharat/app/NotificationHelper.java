package com.pharmabharat.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Build;
import androidx.core.app.NotificationCompat;

public class NotificationHelper {

    public static final String CHANNEL_ID = "pharmly_job_alerts";
    public static final String CHANNEL_NAME = "Pharmly Job Alerts";

    public static void showJobNotification(Context context, String title, String message) {
        try {
            NotificationManager notificationManager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                NotificationChannel channel = new NotificationChannel(
                        CHANNEL_ID,
                        CHANNEL_NAME,
                        NotificationManager.IMPORTANCE_HIGH
                );
                channel.setDescription("Notifications for new pharmacy job openings");
                channel.enableVibration(true);
                if (notificationManager != null) {
                    notificationManager.createNotificationChannel(channel);
                }
            }

            Intent intent = new Intent(context, MainActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent pendingIntent = PendingIntent.getActivity(
                    context,
                    (int) System.currentTimeMillis(),
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );

            Bitmap largeIcon = BitmapFactory.decodeResource(context.getResources(), R.drawable.ic_notification_large);
            if (largeIcon == null) {
                largeIcon = BitmapFactory.decodeResource(context.getResources(), R.drawable.ic_launcher);
            }

            NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_ID)
                    .setSmallIcon(R.drawable.ic_stat_job)
                    .setLargeIcon(largeIcon)
                    .setContentTitle(title)
                    .setContentText(message)
                    .setStyle(new NotificationCompat.BigTextStyle().bigText(message))
                    .setAutoCancel(true)
                    .setContentIntent(pendingIntent)
                    .setPriority(NotificationCompat.PRIORITY_HIGH);

            if (notificationManager != null) {
                notificationManager.notify((int) (System.currentTimeMillis() % 100000), builder.build());
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
