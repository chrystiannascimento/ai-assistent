package com.assistentevoz.callscreening

import android.telecom.Call
import android.telecom.CallScreeningService
import android.telecom.CallScreeningService.CallResponse
import android.util.Log

/**
 * Esqueleto do servico de triagem de chamadas.
 *
 * Por enquanto apenas permite todas as chamadas (nao bloqueia nem intervem).
 * O pipeline de audio (encaminhar a chamada para STT -> orquestrador -> TTS)
 * e o proximo passo, fora do escopo desta fase — ver README.
 */
class AssistenteCallScreeningService : CallScreeningService() {

    override fun onScreenCall(callDetails: Call.Details) {
        Log.d(TAG, "Chamada recebida de ${callDetails.handle}; permitindo (sem triagem ainda)")

        val resposta = CallResponse.Builder()
            .setDisallowCall(false)
            .setRejectCall(false)
            .setSkipCallLog(false)
            .setSkipNotification(false)
            .build()

        respondToCall(callDetails, resposta)
    }

    companion object {
        private const val TAG = "AssistenteCallScreening"
    }
}
