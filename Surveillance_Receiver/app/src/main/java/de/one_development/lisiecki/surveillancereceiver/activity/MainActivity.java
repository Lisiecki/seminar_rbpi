package de.one_development.lisiecki.surveillancereceiver.activity;

import android.os.Bundle;
import android.support.v7.app.ActionBarActivity;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

import de.one_development.lisiecki.surveillancereceiver.R;
import de.one_development.lisiecki.surveillancereceiver.network.udp.AndroidUDPClient;
import de.one_development.lisiecki.surveillancereceiver.network.udp.AndroidUDPServer;


public class MainActivity extends ActionBarActivity implements View.OnClickListener {
    public static final byte INTRUDER_DETECTED = 0x1;
    public static final int PORT = 58333;
    public static final int SIZE = 0x1;

    private static int intruderDetected = 0;

    private TextView intruderDetectedTextView;

    private AndroidUDPClient androidUDPClient;
    private Runnable setIntruderDetectedTextRunnable = new Runnable() {
        @Override
        public void run() {
            intruderDetectedTextView.setText(String.valueOf(intruderDetected));
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        intruderDetectedTextView =
                (TextView) findViewById(R.id.intruder_detected_text_view);
        Button shutdownButton = (Button) findViewById(R.id.shutdown_button);
        shutdownButton.setOnClickListener(this);

        final AndroidUDPServer androidUDPServer = new AndroidUDPServer(PORT);
        androidUDPClient = new AndroidUDPClient(PORT, "255.255.255.255");

        Thread t = new Thread(new Runnable() {
            @Override
            public synchronized void run() {
                while (true) {
                    byte signal = androidUDPServer.readyRead(SIZE)[0];

                    switch (signal) {
                        case INTRUDER_DETECTED:
                            intruderDetected = 100;
                            break;
                        default:
                            intruderDetected -= 5;
                            break;
                    }

                    if (intruderDetected > 100) {
                        intruderDetected = 100;
                    }

                    if (intruderDetected < 0) {
                        intruderDetected = 0;
                    }

                    intruderDetectedTextView.post(setIntruderDetectedTextRunnable);
                }
            }
        });

        t.start();
    }

    @Override
    public void onClick(View view) {
        switch (view.getId()) {
            case R.id.shutdown_button:
                byte[] data = {0x7};
                androidUDPClient.sendData(data);
                break;
        }
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
