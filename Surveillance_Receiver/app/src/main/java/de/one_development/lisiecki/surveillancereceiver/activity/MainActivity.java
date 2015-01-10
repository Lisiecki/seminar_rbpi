package de.one_development.lisiecki.surveillancereceiver.activity;

import android.os.Bundle;
import android.support.v7.app.ActionBarActivity;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.TextView;

import java.io.IOException;

import de.one_development.lisiecki.surveillancereceiver.R;
import de.one_development.lisiecki.surveillancereceiver.network.udp.AndroidUDPServer;


public class MainActivity extends ActionBarActivity {
    public static final int PORT = 58333;
    public static final int SIZE = 0x1;
    public static final long DECREASE_PERCENTAGE_INTERVAL = 10;

    private int intruderDetected = 0;
    private long lastTimeStamp = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        final TextView intruderDetectedTextView =
                (TextView) findViewById(R.id.intruder_detected_text_view);
        final AndroidUDPServer androidUDPServer = new AndroidUDPServer(PORT);

        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                lastTimeStamp = System.currentTimeMillis();

                while (true) {
                    try {
                        int signal = androidUDPServer.readyRead(SIZE)[0];

                        if (signal > 0) {
                            intruderDetected += signal;
                        }
                        else {
                            intruderDetected = 0;
                        }


                        if (intruderDetected > 100 ) {
                            intruderDetected = 100;
                        }

                        if (intruderDetected < 0) {
                            intruderDetected = 0;
                        }

                        intruderDetectedTextView.post(new Runnable() {
                            @Override
                            public void run() {
                                intruderDetectedTextView.setText(String.valueOf(intruderDetected));
                            }
                        });
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                }
            }
        });

        t.start();
    }


    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        // Inflate the menu; this adds items to the action bar if it is present.
        getMenuInflater().inflate(R.menu.menu_main, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        // Handle action bar item clicks here. The action bar will
        // automatically handle clicks on the Home/Up button, so long
        // as you specify a parent activity in AndroidManifest.xml.
        int id = item.getItemId();

        //noinspection SimplifiableIfStatement
        if (id == R.id.action_settings) {
            return true;
        }

        return super.onOptionsItemSelected(item);
    }
}
