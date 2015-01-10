package de.one_development.lisiecki.surveillancereceiver.network.udp;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.SocketException;

/**
 * Created by Dennis on 09.01.2015.
 */
public class AndroidUDPServer {
    DatagramSocket serverDatagramSocket;

    public AndroidUDPServer(int p) {
        try {
            serverDatagramSocket = new DatagramSocket(p);
        } catch (SocketException e) {
            e.printStackTrace();
        }
    }

    public byte[] readyRead(int size) throws IOException {
        byte[] receiveData = new byte[size];
        DatagramPacket receiveDatagramPacket = new DatagramPacket(receiveData, receiveData.length);

        try {
            serverDatagramSocket.setSoTimeout(20);
            serverDatagramSocket.receive(receiveDatagramPacket);
            return receiveDatagramPacket.getData();
        } catch (SocketException e) {
            byte[] retVal = new byte[size];
            retVal[0] = 0;
            return retVal;
        }
    }
}
