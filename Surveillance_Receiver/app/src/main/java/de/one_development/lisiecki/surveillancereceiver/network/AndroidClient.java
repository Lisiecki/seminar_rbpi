package de.one_development.lisiecki.surveillancereceiver.network;

/**
 * Created by Dennis on 27.08.2014.
 */
public abstract class AndroidClient {
    /**
     *
     * @param buffer
     */
    public abstract void sendData(byte[] buffer);

    /**
     *
     * @param buffer
     * @return
     */
    public abstract String sendDataAndGetResponse(byte[] buffer);
}
