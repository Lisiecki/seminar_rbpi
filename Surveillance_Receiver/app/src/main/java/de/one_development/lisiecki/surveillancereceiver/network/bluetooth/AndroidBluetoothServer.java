package de.one_development.lisiecki.surveillancereceiver.network.bluetooth;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothServerSocket;
import android.bluetooth.BluetoothSocket;
import android.content.Intent;

import java.io.IOException;
import java.io.InputStream;
import java.util.UUID;

/**
 * Created by Dennis on 26.08.2014.
 */
public class AndroidBluetoothServer {
    public static final int REQUEST_ENABLE_BT = 1;

    private BluetoothSocket bluetoothSocket;
    private BluetoothServerSocket bluetoothServerSocket;
    private BluetoothAdapter bluetoothAdapter;
    private Activity activity;
    private BluetoothServerListener bluetoothServerListener;
    private InputStream inputStream;

    public AndroidBluetoothServer(Activity act, BluetoothServerListener listener, String uuid, String name) {
        activity = act;
        bluetoothServerListener = listener;
        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();
        if (bluetoothAdapter == null) {
            System.out.println("Device does not support Bluetooth");
        }

        if (!bluetoothAdapter.isEnabled()) {
            activity.startActivityForResult(new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE),
                    REQUEST_ENABLE_BT);
        }

        try {
            bluetoothServerSocket = bluetoothAdapter.listenUsingRfcommWithServiceRecord(name,
                    UUID.fromString(uuid));
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void readyToConnect() {
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                while (true) {
                    try {
                        bluetoothSocket = bluetoothServerSocket.accept();
                        inputStream = bluetoothSocket.getInputStream();
                        if (bluetoothSocket != null) {
                            readyRead();
                            bluetoothServerSocket.close();
                            break;
                        }
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                }
            }
        });
        t.start();
    }

    public void readyRead() {
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                byte[] buffer = new byte[256];
                int bytes;

                while (true) {
                    try {
                        bytes = inputStream.read(buffer);
                        bluetoothServerListener.onRead(bytes, buffer);
                    } catch (IOException e) {
                        e.printStackTrace();
                        break;
                    }
                }
            }
        });
        t.start();
    }

    public interface BluetoothServerListener {
        void onRead(int size, byte[] buffer);
    }
}
