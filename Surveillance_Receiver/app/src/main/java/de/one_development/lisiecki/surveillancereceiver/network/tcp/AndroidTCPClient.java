package de.one_development.lisiecki.surveillancereceiver.network.tcp;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.Socket;
import java.net.UnknownHostException;
import java.util.Scanner;

import de.one_development.lisiecki.surveillancereceiver.network.AndroidClient;

/**
 * Created by Dennis on 26.08.2014.
 */
public class AndroidTCPClient extends AndroidClient implements Runnable {
    private int size;
    private int port;
    private InetAddress serverInetAddress;
    private Scanner input;
    private BufferedReader inputBufferedReader;
    private OutputStream output;

    private Socket server = null;
    private Socket client = null;

    public AndroidTCPClient(int p) {
        try {
            serverInetAddress = InetAddress.getLocalHost();
            port = p;
            server = new Socket(serverInetAddress, port);
        } catch (UnknownHostException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public AndroidTCPClient(int p, String hostname) {
        try {
            serverInetAddress = InetAddress.getByName(hostname);
            port = p;
        } catch (UnknownHostException e) {
            e.printStackTrace();
        }

        Thread t = new Thread(this);
        t.start();
    }

    @Override
    protected void finalize() throws Throwable {
        super.finalize();
        try {
            output.close();
            inputBufferedReader.close();
            server.close();
        } catch (NullPointerException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void run() {
        try {
            server = new Socket(serverInetAddress, port);
            output = server.getOutputStream();
            inputBufferedReader =
                    new BufferedReader(new InputStreamReader(server.getInputStream()));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void sendData(byte[] buffer) {
        try {
            output.write(buffer);
        } catch (UnknownHostException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public String sendDataAndGetResponse(byte[] buffer) {
        String response = "";
        char[] data = new char[1024];

        try {

            System.out.println("Send data");
            output.write(buffer);
            System.out.println("Wait for response");
            while (!inputBufferedReader.ready()) {}
            System.out.println("Get response");
            int i = inputBufferedReader.read(data);
            response = String.valueOf(data, 0 , i-1);
            System.out.println("Response: " + response);

            return response;
        } catch (UnknownHostException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }

        return response;
    }
}
