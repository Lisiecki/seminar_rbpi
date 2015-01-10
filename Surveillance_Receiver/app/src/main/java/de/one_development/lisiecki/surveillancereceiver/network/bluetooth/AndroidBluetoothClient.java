package de.one_development.lisiecki.surveillancereceiver.network.bluetooth;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import android.content.Intent;
import android.os.ParcelUuid;

import java.io.IOException;
import java.io.OutputStream;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

import de.one_development.lisiecki.surveillancereceiver.network.AndroidClient;

/**
 * Created by Dennis on 26.08.2014.
 */
public class AndroidBluetoothClient extends AndroidClient {
    public static final int REQUEST_ENABLE_BT = 1;

    BluetoothSocket bluetoothSocket;
    BluetoothAdapter bluetoothAdapter;
    BluetoothDevice bluetoothDevice;
    Activity activity;
    OutputStream outputStream;

    public AndroidBluetoothClient(Activity act) {
        activity = act;
        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();
        if (bluetoothAdapter == null) {
            return;
        }

        if (!bluetoothAdapter.isEnabled()) {
            activity.startActivityForResult(new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE),
                    REQUEST_ENABLE_BT);
        }
    }

    @Override
    public synchronized void sendData(byte[] buffer) {
        try {
            outputStream.write(buffer);
        } catch (Exception e) {
            try {
                bluetoothSocket.close();
            } catch (IOException ioE) {
                ioE.printStackTrace();
            }
            e.printStackTrace();
        }
    }

    @Override
    protected void finalize() throws Throwable {
        super.finalize();
        try {
            bluetoothSocket.close();
        } catch (NullPointerException e) {
            e.printStackTrace();
        }
    }

    /**
     *
     * @param address
     * @param uuid
     */
    public synchronized void connectTo(String address, String uuid) {
        for (BluetoothDevice device : getBluetoothDevices()) {
            if(device.getAddress().equals(address)) {
                bluetoothDevice = device;
            }
        }

        if (bluetoothDevice != null) {
            bluetoothAdapter.cancelDiscovery();
            try {
                bluetoothSocket = bluetoothDevice.createRfcommSocketToServiceRecord(
                        UUID.fromString(uuid));
                bluetoothSocket.connect();
                outputStream = bluetoothSocket.getOutputStream();
            } catch (IOException e1) {
                try {
                    bluetoothSocket.close();
                } catch (IOException e2) {
                    e2.printStackTrace();
                }
                e1.printStackTrace();
            }
        }
    }

    /**
     *
     * @return
     */
    public BluetoothDevice[] getBluetoothDevices() {
        Set<BluetoothDevice> pairedBthDevicesSet = bluetoothAdapter.getBondedDevices();
        return pairedBthDevicesSet.toArray(new BluetoothDevice[pairedBthDevicesSet.size()]);
    }

    /**
     *
     * @param uuid
     * @return
     */
    public BluetoothDevice[] getBluetoothDevices(String uuid) {
        Set<BluetoothDevice> bondedDevicesSet = bluetoothAdapter.getBondedDevices();
        Set<BluetoothDevice> pairedBthDevicesSet = new HashSet<BluetoothDevice>();

        for (BluetoothDevice device : bondedDevicesSet) {
            for (ParcelUuid id : device.getUuids()) {
                if (id.toString().equals(uuid)) {
                    pairedBthDevicesSet.add(device);
                }
            }
        }

        return pairedBthDevicesSet.toArray(new BluetoothDevice[pairedBthDevicesSet.size()]);
    }

    /**
     *
     * @return
     */
    public boolean isConnected() {
        return bluetoothSocket != null && bluetoothSocket.isConnected();
    }

    public String sendDataAndGetResponse(byte[] buffer) {

        return null;
    }
}
