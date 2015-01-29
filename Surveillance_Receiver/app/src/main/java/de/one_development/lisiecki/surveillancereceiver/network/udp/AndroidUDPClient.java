package de.one_development.lisiecki.surveillancereceiver.network.udp;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.UnknownHostException;

import de.one_development.lisiecki.surveillancereceiver.network.AndroidClient;

public class AndroidUDPClient extends AndroidClient {
	private int port;
	private byte[] message;
	private DatagramSocket socket;
	private InetAddress address;

	public AndroidUDPClient(int p, String ip) {
		try {
			address = InetAddress.getByName(ip);
            port = p;
            socket = new DatagramSocket();
            socket.setBroadcast(true);
        } catch (UnknownHostException e) {
			e.printStackTrace();
		} catch (IOException e) {
            e.printStackTrace();
        }
	}

    @Override
	public synchronized void sendData(final byte[] msg) {
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    System.out.println("msg: " + msg[0]);
                    DatagramPacket packet = new DatagramPacket(msg, msg.length, address, port);
                    socket.send(packet);
                } catch (IOException e) {
                    e.printStackTrace();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        });

        t.start();
	}

    @Override
    protected void finalize() throws Throwable {
        super.finalize();
        try {
            socket.close();
        } catch (NullPointerException e) {
            e.printStackTrace();
        }
    }

    public String sendDataAndGetResponse(byte[] buffer) {
        message = buffer;
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    byte[] msg = message;
                    byte[] rec = new byte[1024];
                    DatagramPacket msgDatagramPacket = new DatagramPacket(msg, msg.length, address, port);
                    DatagramPacket recDatagramPacket = new DatagramPacket(rec, rec.length);
                    socket.send(msgDatagramPacket);
                    socket.receive(recDatagramPacket);
                } catch (IOException e) {
                    e.printStackTrace();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        });

        t.start();
        return null;
    }
}
