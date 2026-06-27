import AVFoundation
import Foundation

@MainActor
final class AudioPlayerService {
    static let shared = AudioPlayerService()

    static let phonemeAudioMap: [String: [String]] = [
        "p": ["ipa_p"],
        "b": ["ipa_b"],
        "t": ["ipa_t"],
        "d": ["ipa_d"],
        "k": ["ipa_k"],
        "g": ["ipa_g"],
        "ɡ": ["ipa_g"],
        "f": ["ipa_f"],
        "v": ["ipa_v"],
        "θ": ["ipa_theta"],
        "ð": ["ipa_eth"],
        "s": ["ipa_s"],
        "z": ["ipa_z"],
        "ʃ": ["ipa_sh"],
        "ʒ": ["ipa_zh"],
        "h": ["ipa_h"],
        "x": ["ipa_x"],
        "m": ["ipa_m"],
        "n": ["ipa_n"],
        "ŋ": ["ipa_ng"],
        "l": ["ipa_l"],
        "ɫ": ["ipa_l"],
        "r": ["ipa_r"],
        "rː": ["ipa_r"],
        "ɹ": ["ipa_r"],
        "ɹː": ["ipa_r"],
        "ɾ": ["ipa_tap"],
        "j": ["ipa_j"],
        "w": ["ipa_w"],
        "ʍ": ["ipa_w_voiceless"],
        "ʔ": ["ipa_glottal_stop"],
        "i": ["ipa_i"],
        "iː": ["ipa_i"],
        "ɪ": ["ipa_i_short"],
        "ɪː": ["ipa_i_short"],
        "e": ["ipa_e"],
        "ɛ": ["ipa_e_open"],
        "ɛː": ["ipa_e_open"],
        "æ": ["ipa_ae"],
        "æː": ["ipa_ae"],
        "ə": ["ipa_schwa"],
        "əː": ["ipa_schwa"],
        "ɜ": ["ipa_er_open"],
        "ɜː": ["ipa_er_open"],
        "ɚ": ["ipa_schwa", "ipa_r"],
        "ɝ": ["ipa_er_open", "ipa_r"],
        "ɝː": ["ipa_er_open", "ipa_r"],
        "ʌ": ["ipa_caret"],
        "ɑ": ["ipa_alpha"],
        "ɑː": ["ipa_alpha"],
        "ɒ": ["ipa_o_open"],
        "ɔ": ["ipa_aw"],
        "ɔː": ["ipa_aw"],
        "œ": ["ipa_oe"],
        "ʊ": ["ipa_u_short"],
        "ʊː": ["ipa_u_short"],
        "u": ["ipa_u"],
        "uː": ["ipa_u"],
        "ɨ": ["ipa_i_bar"],
        "ɵ": ["ipa_o_bar"],
        "ʉ": ["ipa_u_bar"],
        "o": ["ipa_o"],
        "oː": ["ipa_o"],
        "a": ["ipa_a"],
        "aː": ["ipa_a"],
        "sː": ["ipa_s"],
        "tʃ": ["ipa_t_ch"],
        "dʒ": ["ipa_d_zh"],
        "eɪ": ["ipa_e", "ipa_i_short"],
        "eɪː": ["ipa_e", "ipa_i_short"],
        "aɪ": ["ipa_a", "ipa_i_short"],
        "aɪː": ["ipa_a", "ipa_i_short"],
        "ɔɪ": ["ipa_aw", "ipa_i_short"],
        "aʊ": ["ipa_a", "ipa_u_short"],
        "əʊ": ["ipa_schwa", "ipa_u_short"],
        "oʊ": ["ipa_o", "ipa_u_short"],
        "oʊː": ["ipa_o", "ipa_u_short"],
        "ɪə": ["ipa_i_short", "ipa_schwa"],
        "eə": ["ipa_e", "ipa_schwa"],
        "ʊə": ["ipa_u_short", "ipa_schwa"]
    ]

    private var audioPlayer: AVAudioPlayer?
    private var remotePlayer: AVPlayer?
    private var playbackTask: Task<Void, Never>?
    private let speechSynthesizer = AVSpeechSynthesizer()

    private init() {}

    func playSound(fileName: String) {
        playSoundSequence(fileNames: [fileName])
    }

    func playPhoneme(symbol: String) {
        guard let fileNames = Self.phonemeAudioMap[symbol] else {
            print("No local audio mapping for phoneme: \(symbol)")
            return
        }

        playSoundSequence(fileNames: fileNames)
    }

    func playRemoteSound(url: URL) {
        playbackTask?.cancel()
        remotePlayer = AVPlayer(url: url)
        remotePlayer?.play()
    }

    func speak(word: String, region: String) {
        playbackTask?.cancel()
        let utterance = AVSpeechUtterance(string: word)
        utterance.voice = AVSpeechSynthesisVoice(
            language: region == "UK" ? "en-GB" : "en-US"
        )
        utterance.rate = 0.42
        speechSynthesizer.stopSpeaking(at: .immediate)
        speechSynthesizer.speak(utterance)
    }

    private func playSoundSequence(fileNames: [String]) {
        playbackTask?.cancel()
        playbackTask = Task { @MainActor in
            for fileName in fileNames {
                guard !Task.isCancelled,
                      let player = makeAudioPlayer(fileName: fileName) else {
                    continue
                }

                audioPlayer = player
                player.prepareToPlay()
                player.play()

                let duration = max(player.duration, 0.18)
                try? await Task.sleep(
                    nanoseconds: UInt64(duration * 1_000_000_000)
                )
            }
        }
    }

    private func makeAudioPlayer(fileName: String) -> AVAudioPlayer? {
        let file = fileName as NSString
        let resourceName = file.deletingPathExtension
        let fileExtension = file.pathExtension.isEmpty ? "mp3" : file.pathExtension

        let url = Bundle.main.url(
            forResource: resourceName,
            withExtension: fileExtension,
            subdirectory: "Audio/Phonemes"
        ) ?? Bundle.main.url(
            forResource: resourceName,
            withExtension: fileExtension
        )

        guard let url else {
            print("Audio file not found in app bundle: \(resourceName).\(fileExtension)")
            return nil
        }

        do {
            #if os(iOS)
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .spokenAudio)
            try session.setActive(true)
            #endif

            return try AVAudioPlayer(contentsOf: url)
        } catch {
            print("Unable to play \(fileName): \(error.localizedDescription)")
            return nil
        }
    }
}
