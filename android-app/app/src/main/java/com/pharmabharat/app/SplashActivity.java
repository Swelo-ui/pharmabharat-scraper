package com.pharmabharat.app;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import androidx.appcompat.app.AppCompatActivity;

public class SplashActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_splash);

        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            if (!isFinishing() && !isDestroyed()) {
                Intent mainIntent = new Intent(SplashActivity.this, MainActivity.class);
                if (getIntent() != null && getIntent().getExtras() != null) {
                    mainIntent.putExtras(getIntent().getExtras());
                }
                if (getIntent() != null && getIntent().getData() != null) {
                    mainIntent.setData(getIntent().getData());
                }
                startActivity(mainIntent);
                finish();
            }
        }, 1200);
    }
}
